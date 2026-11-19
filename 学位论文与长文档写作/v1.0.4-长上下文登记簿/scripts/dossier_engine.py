#!/usr/bin/env python3
"""dossier_engine.py — 长上下文登记簿与重复论述防护引擎（longdoc-dossier v1.0.4）

解决「数万字长文档读不进一次上下文」的问题：把全文的定义、结论、材料使用情况
登记成 dossier（登记簿），写作时只读按预算生成的 context_brief，写完后用 overlap
复核重复论述 / 重复结论 / 脱节 / 材料遗漏。

子命令（只依赖 Python3 标准库）：
  build   --chapters work/chapters.json --work /app/work [--materials-regex REGEX]
          → work/dossier.json + work/dossier.md
  brief   --dossier work/dossier.json --target-section "第3章 结果与讨论"
          [--budget-chars 3000] --work /app/work → work/context_brief.md
  overlap --draft <新章.md> --chapters work/chapters.json
          --dossier work/dossier.json --work /app/work
          → work/overlap_report.json + work/overlap_report.md

判据与阈值见 references/dossier_rules.md；阈值可用同名参数覆盖。
"""
import argparse, datetime, json, os, re, sys

# ---------------------------------------------------------------- 基础工具

MATERIAL_HINT = re.compile(
    r"(fact|facts|note|notes|reading|material|materials|data|dataset|"
    r"材料|笔记|摘录|数据|事实)", re.I)

ABBR_TOKEN = re.compile(r"\b([A-Z][A-Za-z0-9]{1,9})\b")
# 常见非术语全大写 token（标准号、单位、杂项），不作为「未定义缩写」误报
ABBR_STOPLIST = {"GB", "ISO", "ASTM", "DIN", "JIS", "SI", "OK", "ID", "VS",
                 "PDF", "HTML", "URL", "DOI", "UTF", "ASCII", "JSON", "XML",
                 "I", "A", "B", "C", "D", "E", "N", "P", "R", "T"}

NUM_UNIT = re.compile(
    r"\d+(?:\.\d+)?\s*(?:%|°C|℃|K|mS/cm|S/cm|mS·cm⁻¹|mS·cm-1|h|min|s|V|mV|"
    r"kHz|MHz|Hz|MPa|GPa|Pa|nm|μm|µm|mm|cm|mA|mAh|A|g|mg|kg|mol|wt%|at%|"
    r"rpm|r/min|W|kW|J|kJ|eV|keV|℃|MPa·m)")

CONCL_RE = re.compile(
    r"(表明|说明|证明|综上|由此可知|由此可见|得出结论|结论是|"
    r"\bconcludes?\b|\bconclusion\b|\bdemonstrat\w+\b|"
    r"\bshow(?:s|ed|n)?\s+that\b|\bindicat\w+\s+that\b|\bsuggest\w+\s+that\b)",
    re.I)

# 定义句模式
DEF_ABBR_FULL = re.compile(   # 中文全称（English full name, ABBR）
    r"([一-鿿][一-鿿A-Za-z0-9·\-]{1,29}?)（([A-Za-z][A-Za-z\-\s]{1,60}?)[,，]\s*"
    r"([A-Z][A-Za-z0-9]{1,9})）")
DEF_ABBR_CN = re.compile(     # 中文全称（ABBR）
    r"([一-鿿][一-鿿A-Za-z0-9·\-]{1,19}?)（([A-Z][A-Za-z0-9]{1,9})）")
DEF_ABBR_EN = re.compile(     # english full name (ABBR)
    r"([A-Za-z][A-Za-z\-\s]{2,60}?)\s*\(([A-Z][A-Za-z0-9]{1,9})\)")
DEF_COPULA_CN = re.compile(   # X 是指/定义为/记为/即 …
    r"(?:^|[，,。；;：:\s])([一-鿿A-Za-z][一-鿿A-Za-z0-9\-]{1,29}?)\s*"
    r"(?:是指|指的是|被定义为|定义为|记为|记作|即指)\s*[：:]?\s*(.{2,200})")
DEF_COPULA_EN = re.compile(
    r"\b([A-Za-z][\w\- ]{1,40}?)\s+(?:is defined as|is denoted as|is denoted by|"
    r"refers to|denotes)\s+(.{2,200})", re.I)
DEF_LET_EN = re.compile(
    r"\blet\s+([\w\- ]{1,30}?)\s+(?:denote|represent|be)\s+(.{2,200})", re.I)

FIGTAB_REF = re.compile(r"(图|表|Fig(?:ure)?\.?|Table\.?)\s*(\d+(?:[-–.]\d+)?)")
CAPTION_START = re.compile(r"^(图|表|Fig(?:ure)?\.?|Table\.?)\s*(\d+(?:[-–.]\d+)?)")


def norm_text(s):
    """归一化：小写、仅保留中英数字，供 n-gram 相似度使用。"""
    return re.sub(r"[^一-鿿a-z0-9]", "", s.lower())


def ngrams(s, n):
    t = norm_text(s)
    if len(t) < n:
        return {t} if t else set()
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def split_sentences(text):
    """中英文句子切分；小数点（3.2）不切。"""
    parts = re.split(r"(?<=[。！？；!?;])|(?<=\.)(?!\d)", text)
    return [p.strip() for p in parts if len(p.strip()) >= 4]


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ---------------------------------------------------------------- build

def extract_definitions(paragraphs, pid2chapter):
    """从全部段落抽取定义句与缩写定义。返回 (definitions, seen_keys)。"""
    defs = []
    seen = set()

    LEAD_VERB = re.compile(
        r"^(?:是指|指的是|是|为|即|采用|使用|利用|称作|称为|所谓|用)")

    def add(term, abbr, en, definition, pid):
        term = LEAD_VERB.sub("", (term or "").strip(" ，,。；;：:"))
        definition = (definition or "").strip()
        if not term or len(term) > 40:
            return
        key = (abbr or term).lower()
        if key in seen:
            return
        seen.add(key)
        defs.append({"term": term, "abbr": abbr, "en": (en or "").strip() or None,
                     "definition": definition[:300],
                     "first_pid": pid, "chapter": pid2chapter.get(pid)})

    for p in paragraphs:
        pid, text = p["pid"], p["text"]
        for m in DEF_ABBR_FULL.finditer(text):
            t = LEAD_VERB.sub("", m.group(1))
            add(m.group(1), m.group(3), m.group(2),
                f"{t}（{m.group(2)}, {m.group(3)}）", pid)
        for m in DEF_ABBR_CN.finditer(text):
            t = LEAD_VERB.sub("", m.group(1))
            add(m.group(1), m.group(2), None,
                f"{t}（{m.group(2)}）", pid)
        for m in DEF_ABBR_EN.finditer(text):
            tail = m.group(1).strip().split()[-6:]
            add(" ".join(tail), m.group(2), m.group(1).strip(),
                f"{m.group(1).strip()} ({m.group(2)})", pid)
        for sent in split_sentences(text):
            for m in DEF_COPULA_CN.finditer(sent):
                add(m.group(1), None, None, m.group(2).strip(), pid)
            for m in DEF_COPULA_EN.finditer(sent):
                add(m.group(1), None, None, m.group(2).strip(), pid)
            for m in DEF_LET_EN.finditer(sent):
                add(m.group(1), None, None, m.group(2).strip(), pid)
    return defs, seen


def extract_conclusions(paragraphs, pid2chapter):
    out = []
    for p in paragraphs:
        if p["kind"] in ("heading", "reference_list", "caption",
                         "figure_note", "table_note", "equation_note"):
            continue
        for sent in split_sentences(p["text"]):
            if CONCL_RE.search(sent):
                nums = [m.group(0).strip() for m in NUM_UNIT.finditer(sent)]
                out.append({"pid": p["pid"], "sentence": sent[:300],
                            "chapter": pid2chapter.get(p["pid"]),
                            "key_numbers": nums})
    return out


def classify_files(chapters, materials_regex):
    """把文件分为 稿件章节 / 事实材料 两类。"""
    rx = re.compile(materials_regex, re.I) if materials_regex else MATERIAL_HINT
    mat, mans = [], []
    for f in chapters.get("files", []):
        base = os.path.basename(f.get("path", ""))
        (mat if rx.search(base) else mans).append(f["key"])
    return mat, mans


def build_material_usage(chapters, mat_keys, man_keys, threshold):
    mat_paras = [p for s in chapters["sections"] if s["file_key"] in mat_keys
                 for p in s["paragraphs"]
                 if p["kind"] in ("body", "list", "appendix", "footnote")
                 and len(norm_text(p["text"])) >= 8]
    man_paras = [p for s in chapters["sections"] if s["file_key"] in man_keys
                 for p in s["paragraphs"]
                 if p["kind"] in ("body", "list", "appendix", "footnote")
                 and len(norm_text(p["text"])) >= 8]
    man_grams = [(p["pid"], ngrams(p["text"], 2)) for p in man_paras]
    usage, omissions = [], []
    for mp in mat_paras:
        mg = ngrams(mp["text"], 2)
        used_by = []
        for pid, g in man_grams:
            sc = jaccard(mg, g)
            if sc >= threshold:
                used_by.append({"pid": pid, "score": round(sc, 3)})
        used_by.sort(key=lambda x: -x["score"])
        entry = {"material_pid": mp["pid"], "text": mp["text"][:300],
                 "used_by": used_by}
        usage.append(entry)
        if not used_by:
            omissions.append({"pid": mp["pid"], "text": mp["text"][:300]})
    return usage, omissions


def build_glossary(paragraphs, definitions):
    """缩写/术语首现表 + 脱节候选（使用早于定义）。"""
    order = {p["pid"]: i for i, p in enumerate(paragraphs)}
    defined = {}
    for d in definitions:
        for tok in ([d["abbr"]] if d.get("abbr") else []) + [d["term"]]:
            if tok and tok not in defined:
                defined[tok] = d["first_pid"]
    observed = {}
    for p in paragraphs:
        for m in ABBR_TOKEN.finditer(p["text"]):
            tok = m.group(1)
            if tok in ABBR_STOPLIST or len(tok) < 2:
                continue
            if tok not in observed:
                observed[tok] = p["pid"]
    entries = []
    for tok in sorted(set(list(defined) + list(observed))):
        def_pid = defined.get(tok)
        first = observed.get(tok, def_pid)
        detached = bool(def_pid and first and
                        order.get(first, 0) < order.get(def_pid, 0)
                        and tok.isupper())
        entries.append({"token": tok, "kind": "abbr" if tok.isupper() else "term",
                        "first_pid": first, "definition_pid": def_pid,
                        "detached_use": detached})
    return entries


def collect_captions(paragraphs):
    caps = []
    for p in paragraphs:
        if p["kind"] in ("figure_note", "table_note", "caption"):
            m = CAPTION_START.match(p["text"].strip())
            if m:
                kind = "figure" if m.group(1) in ("图", "Fig", "Figure", "Fig.", "Figure.") else "table"
                caps.append({"kind": kind, "number": m.group(2),
                             "pid": p["pid"], "text": p["text"][:200]})
    return caps


def cmd_build(args):
    chapters = load_json(args.chapters)
    if not chapters or "sections" not in chapters:
        print(f"[dossier build][FAIL] chapters.json 不可解析: {args.chapters}",
              file=sys.stderr)
        return 2
    paragraphs = chapters.get("paragraphs", [])
    pid2chapter = {}
    for s in chapters["sections"]:
        for p in s["paragraphs"]:
            pid2chapter[p["pid"]] = s["title"]

    definitions, _ = extract_definitions(paragraphs, pid2chapter)
    conclusions = extract_conclusions(paragraphs, pid2chapter)
    mat_keys, man_keys = classify_files(chapters, args.materials_regex)
    usage, omissions = build_material_usage(chapters, set(mat_keys),
                                            set(man_keys), args.usage_threshold)
    glossary = build_glossary(paragraphs, definitions)
    captions = collect_captions(paragraphs)

    dossier = {
        "generated_at": now_iso(),
        "source_chapters": args.chapters,
        "thresholds": {"material_usage_jaccard2": args.usage_threshold,
                       "overlap_sentence_4gram": args.overlap_threshold,
                       "omission_reminder_jaccard2": args.remind_threshold},
        "material_files": mat_keys, "manuscript_files": man_keys,
        "definitions": definitions,
        "conclusions": conclusions,
        "material_usage": usage,
        "omissions": omissions,
        "glossary_first_use": glossary,
        "captions": captions,
        "stats": {"n_definitions": len(definitions),
                  "n_conclusions": len(conclusions),
                  "n_material_paragraphs": len(usage),
                  "n_used_material": sum(1 for u in usage if u["used_by"]),
                  "n_omissions": len(omissions),
                  "n_glossary": len(glossary),
                  "n_captions": len(captions),
                  "n_detached_uses": sum(1 for g in glossary if g["detached_use"])},
    }
    os.makedirs(args.work, exist_ok=True)
    with open(os.path.join(args.work, "dossier.json"), "w", encoding="utf-8") as f:
        json.dump(dossier, f, ensure_ascii=False, indent=2)

    md = ["# 上下文登记簿（dossier）", "",
          f"生成时间：{dossier['generated_at']}　来源：{args.chapters}", "",
          f"- 定义 {len(definitions)} 条｜结论 {len(conclusions)} 条｜"
          f"材料段落 {len(usage)} 段（已用 {dossier['stats']['n_used_material']}，"
          f"未用 {len(omissions)}）｜术语首现 {len(glossary)} 条｜"
          f"图表 caption {len(captions)} 条", "",
          "## 1. 定义登记（definitions）", ""]
    for d in definitions:
        ab = f"｜缩写 **{d['abbr']}**" if d.get("abbr") else ""
        md.append(f"- **{d['term']}**{ab}（{d['first_pid']}，{d['chapter']}）："
                  f"{d['definition']}")
    md += ["", "## 2. 已下结论（conclusions）", ""]
    for c in conclusions:
        kn = f"　关键数值：{'、'.join(c['key_numbers'])}" if c["key_numbers"] else ""
        md.append(f"- （{c['pid']}，{c['chapter']}）{c['sentence']}{kn}")
    md += ["", "## 3. 材料使用矩阵（material_usage）", ""]
    for u in usage:
        if u["used_by"]:
            by = "、".join(f"{x['pid']}({x['score']})" for x in u["used_by"][:5])
            md.append(f"- [已用] {u['material_pid']}：{u['text'][:80]}… ← {by}")
        else:
            md.append(f"- [未用] {u['material_pid']}：{u['text'][:100]}")
    md += ["", "## 4. 术语/缩写首现表（glossary_first_use）", ""]
    for g in glossary:
        flag = "　⚠ 使用早于定义（脱节候选）" if g["detached_use"] else ""
        md.append(f"- {g['token']}：首现 {g['first_pid']}，"
                  f"定义 {g['definition_pid'] or '（无）'}{flag}")
    if captions:
        md += ["", "## 5. 图表 caption 清单", ""]
        for c in captions:
            md.append(f"- {('图' if c['kind']=='figure' else '表')}{c['number']}"
                      f"（{c['pid']}）：{c['text'][:80]}")
    md.append("")
    with open(os.path.join(args.work, "dossier.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    st = dossier["stats"]
    print(f"[dossier build] 定义={st['n_definitions']} 结论={st['n_conclusions']} "
          f"材料={st['n_material_paragraphs']}(未用{st['n_omissions']}) "
          f"术语={st['n_glossary']}(脱节候选{st['n_detached_uses']}) "
          f"caption={st['n_captions']} -> work/dossier.json + dossier.md")
    if not mat_keys:
        print("[dossier build][WARN] 未识别出材料文件（可用 --materials-regex 指定），"
              "material_usage/omissions 为空", file=sys.stderr)
    return 0


# ---------------------------------------------------------------- brief

def cmd_brief(args):
    dossier = load_json(args.dossier)
    if not dossier:
        print(f"[dossier brief][FAIL] dossier.json 不可解析: {args.dossier}",
              file=sys.stderr)
        return 2
    target = args.target_section
    tg = ngrams(target, 2)
    budget = args.budget_chars

    def rel(text):
        return jaccard(tg, ngrams(text, 2))

    buckets = [
        ("前文相关定义（引用术语必须沿用这些写法）",
         [(rel(d["term"] + (d.get("abbr") or "") + d["definition"]),
           f"- **{d['term']}**"
           + (f"（{d['abbr']}）" if d.get("abbr") else "")
           + f"：{d['definition']}（首现 {d['first_pid']}，{d['chapter']}）")
          for d in dossier.get("definitions", [])]),
        ("前文已下结论（不得当作新结论重复宣称）",
         [(rel(c["sentence"]),
           f"- （{c['pid']}，{c['chapter']}）{c['sentence']}"
           + (f"　关键数值：{'、'.join(c['key_numbers'])}" if c["key_numbers"] else ""))
          for c in dossier.get("conclusions", [])]),
        ("未用材料提醒（与本节相关的应尽量纳入，避免遗漏）",
         [(rel(o["text"]),
           f"- （{o['pid']}）{o['text']}")
          for o in dossier.get("omissions", [])]),
        ("已被前文使用的材料（复述时须换论证角度，避免重复论述）",
         [(rel(u["text"]),
           f"- （{u['material_pid']}）{u['text'][:120]} ← 已用于 "
           + "、".join(x["pid"] for x in u["used_by"][:3]))
          for u in dossier.get("material_usage", []) if u["used_by"]]),
        ("已有图表 caption（新图/表编号须在其后续编）",
         [(rel(c["text"]),
           f"- {('图' if c['kind']=='figure' else '表')}{c['number']}"
           f"（{c['pid']}）：{c['text'][:80]}")
          for c in dossier.get("captions", [])]),
    ]

    lines = ["# 写作上下文摘要（context_brief）", "",
             f"目标章节：**{target}**　字符预算：{budget}", "",
             "> 本摘要由 dossier_engine.py 从 dossier.json 按相关性（目标标题与条目"
             " 2-gram Jaccard）排序生成；写作时读本摘要即可，无需通读全文。", ""]
    used = sum(len(x) + 1 for x in lines)
    trunc = {}
    for title, items in buckets:
        items = [(sc, ln) for sc, ln in items]
        items.sort(key=lambda x: -x[0])
        kept, dropped = [], 0
        lines.append(f"## {title}")
        lines.append("")
        used += len(title) + 3
        for sc, ln in items:
            if used + len(ln) + 1 > budget:
                dropped += 1
                continue
            kept.append((sc, ln))
            lines.append(ln)
            used += len(ln) + 1
        if not kept:
            lines.append("- （无）")
            used += 8
        lines.append("")
        used += 1
        trunc[title.split("（")[0]] = {"total": len(items),
                                      "kept": len(kept), "dropped": dropped}
    lines += ["---", "## 截断记录（如实登记）", ""]
    for k, v in trunc.items():
        lines.append(f"- {k}：候选 {v['total']} 条，纳入 {v['kept']} 条，"
                     f"因预算截断 {v['dropped']} 条")
    lines.append("")
    with open(os.path.join(args.work, "context_brief.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines))
    total_dropped = sum(v["dropped"] for v in trunc.values())
    print(f"[dossier brief] 目标「{target}」预算 {budget} 字，"
          f"截断 {total_dropped} 条 -> work/context_brief.md")
    return 0


# ---------------------------------------------------------------- overlap

def cmd_overlap(args):
    chapters = load_json(args.chapters)
    dossier = load_json(args.dossier)
    if not chapters or not dossier:
        print("[dossier overlap][FAIL] chapters/dossier 不可解析", file=sys.stderr)
        return 2
    try:
        with open(args.draft, encoding="utf-8") as f:
            draft_text = f.read()
    except OSError as e:
        print(f"[dossier overlap][FAIL] 无法读取 draft: {e}", file=sys.stderr)
        return 2

    draft_paras = [p.strip() for p in re.split(r"\n\s*\n", draft_text) if p.strip()]
    if len(draft_paras) <= 1:
        draft_paras = [l.strip() for l in draft_text.splitlines() if l.strip()]
    draft_sents = []
    for i, p in enumerate(draft_paras, 1):
        if p.startswith("#"):
            continue
        for s in split_sentences(p):
            draft_sents.append({"pid": f"D-P{i:03d}", "sentence": s})
    draft_norm_len = len(norm_text(draft_text))

    # 已有章节（排除材料文件）句子
    mat_keys = set(dossier.get("material_files", []))
    exist_sents = []
    for s in chapters["sections"]:
        if s["file_key"] in mat_keys:
            continue
        for p in s["paragraphs"]:
            if p["kind"] in ("heading", "reference_list"):
                continue
            for sent in split_sentences(p["text"]):
                exist_sents.append({"pid": p["pid"], "sentence": sent,
                                    "chapter": s["title"]})

    # (a) 重复论述：句子级 4-gram Jaccard ≥ 阈值
    dup_expo = []
    exist_grams = [(e, ngrams(e["sentence"], 4))
                   for e in exist_sents if len(norm_text(e["sentence"])) >= 10]
    for ds in draft_sents:
        if len(norm_text(ds["sentence"])) < 10:
            continue
        g = ngrams(ds["sentence"], 4)
        best = None
        for e, eg in exist_grams:
            sc = jaccard(g, eg)
            if sc >= args.overlap_threshold and (best is None or sc > best[0]):
                best = (sc, e)
        if best:
            dup_expo.append({"draft_pid": ds["pid"],
                             "draft_sentence": ds["sentence"][:200],
                             "existing_pid": best[1]["pid"],
                             "existing_chapter": best[1]["chapter"],
                             "existing_sentence": best[1]["sentence"][:200],
                             "score": round(best[0], 3)})

    # (b) 重复结论：draft 结论句 vs dossier 已下结论（同主语重复声明）
    def_terms = set()
    for d in dossier.get("definitions", []):
        if d.get("abbr"):
            def_terms.add(d["abbr"])
        def_terms.add(d["term"])
    # 化学式/复合大写实体（Li6PS5Cl 等）也作为主语判据
    ENTITY_RE = re.compile(r"\b[A-Z][a-z]?(?:\d*[A-Z][a-z]?)+\d*\b")

    def subjects(sent):
        return ({t for t in def_terms if t and t in sent}
                | set(ENTITY_RE.findall(sent)))

    dup_concl = []
    for ds in draft_sents:
        if not CONCL_RE.search(ds["sentence"]):
            continue
        d_nums = {m.group(0).replace(" ", "")
                  for m in NUM_UNIT.finditer(ds["sentence"])}
        d_subj = subjects(ds["sentence"])
        g4 = ngrams(ds["sentence"], 4)
        for c in dossier.get("conclusions", []):
            c_subj = subjects(c["sentence"])
            shared_term = bool(d_subj & c_subj)
            subj_sim = jaccard(ngrams(ds["sentence"], 2),
                               ngrams(c["sentence"], 2))
            if not (shared_term or subj_sim >= 0.25):
                continue  # 不同主语
            c_nums = {n.replace(" ", "") for n in c.get("key_numbers", [])}
            shared_num = bool(d_nums & c_nums)
            sim4 = jaccard(g4, ngrams(c["sentence"], 4))
            if shared_num or sim4 >= 0.3:
                dup_concl.append({
                    "draft_pid": ds["pid"],
                    "draft_sentence": ds["sentence"][:200],
                    "existing_pid": c["pid"],
                    "existing_chapter": c["chapter"],
                    "existing_sentence": c["sentence"][:200],
                    "reason": ("共享关键数值 " + "、".join(sorted(d_nums & c_nums))
                               if shared_num else f"句子 4-gram 相似 {sim4:.2f}")})

    # (c) 脱节：未定义缩写 / 术语 + 悬空图表引用
    defined_abbrs = {d["abbr"] for d in dossier.get("definitions", [])
                     if d.get("abbr")}
    # draft 自身定义也算已定义
    draft_defs, _ = extract_definitions([{"pid": "D", "text": draft_text}], {})
    draft_defined = {d["abbr"] for d in draft_defs if d.get("abbr")}
    prev_tokens = {g["token"] for g in dossier.get("glossary_first_use", [])}
    undefined = []
    seen_tok = set()
    for ds in draft_sents:
        for m in ABBR_TOKEN.finditer(ds["sentence"]):
            tok = m.group(1)
            # 仅全大写且含 ≥2 个字母的 token 视为缩写候选
            # （排除 Li6PS5Cl 化学式、B7 批次号等非缩写 token）
            if tok != tok.upper() or sum(c.isalpha() for c in tok) < 2:
                continue
            if (tok in ABBR_STOPLIST or tok in defined_abbrs
                    or tok in draft_defined or tok in seen_tok):
                continue
            seen_tok.add(tok)
            # 前文出现过但同样未定义 → warning（沿用风险，如实记录不判脱节）；
            # 前文从未出现且未定义 → critical（真脱节，如 draft 首次引入 HRTEM）
            critical = tok not in prev_tokens
            undefined.append({
                "token": tok, "draft_pid": ds["pid"],
                "context": ds["sentence"][:120],
                "severity": "critical" if critical else "warning",
                "note": ("前文无定义且本稿未定义（脱节，须在文中给出全称定义）"
                         if critical else
                         "前文出现过但同样未定义（沿用风险，建议补定义）")})
    n_undef_crit = sum(1 for u in undefined if u["severity"] == "critical")

    cap_keys = {(c["kind"], c["number"].replace("–", "-"))
                for c in dossier.get("captions", [])}
    for p in draft_paras:
        m = CAPTION_START.match(p.strip())
        if m:
            kind = "figure" if m.group(1).startswith(("图", "Fig")) else "table"
            cap_keys.add((kind, m.group(2).replace("–", "-")))
    dangling = []
    seen_ref = set()
    for m in FIGTAB_REF.finditer(draft_text):
        kind = "figure" if m.group(1).startswith(("图", "Fig")) else "table"
        num = m.group(2).replace("–", "-")
        if (kind, num) not in cap_keys and (kind, num) not in seen_ref:
            seen_ref.add((kind, num))
            dangling.append({"kind": kind, "number": num, "raw": m.group(0),
                             "note": "已解析章节与本稿中均无对应 caption"})

    # (d) 未用材料提醒：omissions 与 draft 最相关段落的 2-gram Jaccard ≥ 阈值
    # （按段落比较，避免全文与短材料条目的规模悬殊稀释相关性）
    draft_pg = [ngrams(p, 2) for p in draft_paras if len(norm_text(p)) >= 8]
    reminders = []
    for o in dossier.get("omissions", []):
        og = ngrams(o["text"], 2)
        sc = max((jaccard(og, pg) for pg in draft_pg), default=0.0)
        if sc >= args.remind_threshold:
            reminders.append({"material_pid": o["pid"], "text": o["text"],
                              "score": round(sc, 3)})
    reminders.sort(key=lambda x: -x["score"])

    n_crit = len(dup_expo) + len(dup_concl) + n_undef_crit + len(dangling)
    report = {
        "generated_at": now_iso(), "draft": args.draft,
        "thresholds": {"sentence_4gram_jaccard": args.overlap_threshold,
                       "omission_reminder_jaccard2": args.remind_threshold},
        "counts": {"repeated_exposition": len(dup_expo),
                   "repeated_conclusions": len(dup_concl),
                   "undefined_abbrs": len(undefined),
                   "undefined_abbrs_critical": n_undef_crit,
                   "dangling_figtab": len(dangling),
                   "omission_reminders": len(reminders),
                   "critical_total": n_crit},
        "repeated_exposition": dup_expo,
        "repeated_conclusions": dup_concl,
        "undefined_abbrs": undefined,
        "dangling_figtab": dangling,
        "omission_reminders": reminders,
        "draft_char_count_norm": draft_norm_len,
        "verdict": ("CLEAN" if n_crit == 0 and not reminders else
                    "PASS_WITH_REMINDERS" if n_crit == 0 else "HAS_ISSUES"),
    }
    with open(os.path.join(args.work, "overlap_report.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    md = ["# 重叠/脱节复核报告（overlap_report）", "",
          f"草稿：{args.draft}　判定：**{report['verdict']}**", "",
          f"- 重复论述 {len(dup_expo)} 处｜重复结论 {len(dup_concl)} 处｜"
          f"未定义缩写 {len(undefined)} 个｜悬空图表引用 {len(dangling)} 处｜"
          f"未用材料提醒 {len(reminders)} 条", "",
          "## (a) 重复论述（draft 与已有章节句子级 4-gram 重叠）", ""]
    for d in dup_expo:
        md.append(f"- [{d['score']}] draft {d['draft_pid']}：「{d['draft_sentence'][:80]}」"
                  f" ≈ {d['existing_pid']}（{d['existing_chapter']}）："
                  f"「{d['existing_sentence'][:80]}」")
    md += ["", "## (b) 重复结论（同主语重复声明）", ""]
    for d in dup_concl:
        md.append(f"- draft {d['draft_pid']}：「{d['draft_sentence'][:80]}」"
                  f" ≈ 已有结论 {d['existing_pid']}（{d['existing_chapter']}）："
                  f"「{d['existing_sentence'][:80]}」（{d['reason']}）")
    md += ["", "## (c1) 脱节：未定义缩写/术语", ""]
    for u in undefined:
        md.append(f"- [{u['severity']}] **{u['token']}**（{u['draft_pid']}）："
                  f"{u['context']}…——{u['note']}")
    md += ["", "## (c2) 脱节：悬空图表引用", ""]
    for d in dangling:
        md.append(f"- {d['raw']}：{d['note']}")
    md += ["", "## (d) 未用材料提醒（与草稿主题相关，考虑纳入）", ""]
    for r in reminders:
        md.append(f"- [{r['score']}] （{r['material_pid']}）{r['text']}")
    md.append("")
    with open(os.path.join(args.work, "overlap_report.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(md))
    c = report["counts"]
    print(f"[dossier overlap] verdict={report['verdict']} 重复论述={c['repeated_exposition']} "
          f"重复结论={c['repeated_conclusions']} "
          f"未定义缩写={c['undefined_abbrs']}(critical {c['undefined_abbrs_critical']}) "
          f"悬空图表={c['dangling_figtab']} 材料提醒={c['omission_reminders']} "
          f"-> work/overlap_report.json + overlap_report.md")
    return 0


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(prog="dossier_engine.py",
                                 description="长上下文登记簿与重复论述防护引擎")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="构建上下文登记簿 dossier.json/.md")
    b.add_argument("--chapters", required=True)
    b.add_argument("--work", default="/app/work")
    b.add_argument("--materials-regex", default=None,
                   help="材料文件名识别正则（默认内置 fact/note/material/材料/笔记 等）")
    b.add_argument("--usage-threshold", type=float, default=0.15,
                   help="材料使用判定 2-gram Jaccard 阈值（默认 0.15）")
    b.add_argument("--overlap-threshold", type=float, default=0.6)
    b.add_argument("--remind-threshold", type=float, default=0.1)
    b.set_defaults(fn=cmd_build)

    r = sub.add_parser("brief", help="为待写章节生成受预算约束的上下文摘要")
    r.add_argument("--dossier", required=True)
    r.add_argument("--target-section", required=True)
    r.add_argument("--budget-chars", type=int, default=3000)
    r.add_argument("--work", default="/app/work")
    r.set_defaults(fn=cmd_brief)

    o = sub.add_parser("overlap", help="新章节重复论述/脱节/遗漏复核")
    o.add_argument("--draft", required=True)
    o.add_argument("--chapters", required=True)
    o.add_argument("--dossier", required=True)
    o.add_argument("--work", default="/app/work")
    o.add_argument("--overlap-threshold", type=float, default=0.6,
                   help="重复论述句子 4-gram Jaccard 阈值（默认 0.6）")
    o.add_argument("--remind-threshold", type=float, default=0.1,
                   help="未用材料相关性 2-gram Jaccard 阈值（默认 0.1）")
    o.set_defaults(fn=cmd_overlap)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
