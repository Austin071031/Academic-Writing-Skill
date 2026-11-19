#!/usr/bin/env python3
"""consistency_engine.py — 长文档跨章节一致性维护引擎（连得上）。

子命令（纯 Python3 标准库，输入 chapters.json 由 parse_chapters.py 生成）：

  scan      --chapters work/chapters.json --work /app/work
    产出:
      work/glossary_candidates.json      术语候选（缩写定义型 / 引号书名号型 / 高频复合词）
      work/xref_audit.json               交叉引用一致性（dangling=critical / unreferenced=warn /
                                         编号连续性）——validate_output.py 消费 dangling 字段
      work/contradiction_candidates.json 跨章结论句矛盾候选（供 Agent 裁决，不自动判错）

  glossary  --chapters work/chapters.json --review work/glossary_review.json --work /app/work
    Agent 审定术语候选后写 glossary_review.json：
      [{"canonical": "...", "variants": [...], "definition_pid": "...", "keep": true}, ...]
    产出:
      work/glossary.md                   术语表（canonical | 异写 | 定义位置）
      work/consistency_report.json/.md   同概念异写逐处清单（pid+原文）、异写率、符号冲突

  impact    --chapters work/chapters.json [--glossary work/glossary.md]
            [--changed-term X | --changed-sid C01-S001] --work /app/work
    产出 work/impact_report.json/.md：一处改动（术语或章节）波及的段落 pid 清单
    （引用该术语 / xref 指向该章 / 结论句主语重叠）。

判据与阈值见 references/consistency_rules.md；本文件实现与该文档保持一致。
"""
import argparse, json, os, re, sys, unicodedata
from collections import Counter, defaultdict

# ---------------- 判据常量（与 references/consistency_rules.md 保持一致） ----------------
SUBJECT_OVERLAP_MIN = 0.3          # 结论句主语 n-gram 重叠阈值
NEG_WORDS = ["不", "未", "无法", "不能", "并无", "并未", "no", "not", "fail", "n't", "cannot", "never"]
CONCL_WORDS = ["表明", "说明", "证明", "综上", "得出", "可见", "由此", "据此",
               "conclude", "show", "demonstrate", "indicate", "suggest", "prove"]
HFREQ_MIN_COUNT = 3                # 高频复合词最小出现次数
ZH_NGRAM_RANGE = (4, 8)            # 中文复合词候选长度
EN_PHRASE_RANGE = (2, 3)           # 英文短语候选词数
MAX_CANDIDATES = 60                # 每类术语候选输出上限

# 缩写定义模式
PAT_ZH_EN_ABBR = re.compile(       # 中文（english full, ABBR）/ 中文（english full）
    r"([\u4e00-\u9fff][\u4e00-\u9fff0-9A-Za-z\-]{1,29})"
    r"[（(]([A-Za-z][A-Za-z0-9\- ]{2,60}?)"
    r"(?:\s*[,，]\s*([A-Z][A-Za-z0-9]{1,9}))?[)）]")
# 中文术语左侧黏着的动词/虚词，提取时剥离（如"是全固态电池"→"全固态电池"）
ZH_LEAD_STRIP = ["是基于", "采用", "利用", "通过", "称为", "叫做", "简称", "缩写为",
                 "是", "为", "称", "即", "叫", "用", "了", "的", "和", "与", "及",
                 "在", "由", "将", "并", "其", "该", "此", "对", "把", "被"]

def clean_zh_term(t):
    changed = True
    while changed and len(t) > 2:
        changed = False
        for w in ZH_LEAD_STRIP:
            if t.startswith(w) and len(t) - len(w) >= 2:
                t = t[len(w):]; changed = True; break
    return t
PAT_ABBR_EN = re.compile(          # ABBR (english full)，如 PSCs (perovskite solar cells)
    r"\b([A-Z][A-Za-z0-9]{1,9})\s*[（(]([a-z][A-Za-z0-9\- ]{2,60}?)[)）]")
PAT_QUOTED = re.compile(r"[「『]([^「」『』]{2,20})[」』]|《([^《》]{2,30})》|“([^“”]{2,20})”")
ZH_RUN = re.compile(r"[\u4e00-\u9fff]+")
EN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-]*")
EN_STOP = {"the", "a", "an", "of", "and", "or", "in", "on", "for", "to", "with",
           "is", "are", "was", "were", "by", "at", "as", "from", "we", "our", "this",
           "that", "these", "those", "it", "its", "be", "been", "has", "have", "had"}
SENT_SPLIT = re.compile(r"[。！？!？；;]|(?<=[a-z0-9%\)\]])\.\s+")
DEF_KINDS = {"figure_note", "table_note", "equation_note", "caption"}
FIG_DEF = re.compile(r"^(图|Fig(?:ure)?\.?)\s*(\d+(?:[-–.]\d+)?)")
TAB_DEF = re.compile(r"^(表|Table\.?)\s*(\d+(?:[-–.]\d+)?)")
EQ_DEF = re.compile(r"^(式|公式|Eq\.?|Equation\.?)\s*[（(]?(\d+(?:[-–.]\d+)?)[)）]?")

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def dump_json(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def body_paragraphs(chapters):
    return [p for p in chapters.get("paragraphs", [])
            if p.get("kind") not in ("heading", "reference_list")]

# ---------------- 术语规范化 ----------------
def normalize(term):
    """小写化 + 全半角统一 + 连字符/空白归一 + 英文单复数粗归一。"""
    t = unicodedata.normalize("NFKC", term).lower()
    t = t.replace("–", "-").replace("—", "-").replace("−", "-")
    t = re.sub(r"[\s_]+", "-", t.strip())
    t = re.sub(r"-{2,}", "-", t).strip("-")
    if re.fullmatch(r"[a-z0-9\-]+", t):
        t = re.sub(r"([^s])s$", r"\1", t)   # 粗单复数：ys→y 之外去尾 s
        t = re.sub(r"ies$", "y", t)
    return t

# ---------------- 1. 术语候选扫描 ----------------
def scan_abbr_definitions(paras):
    """(a) 缩写定义型：中文（english, ABBR）/ 中文（english）/ ABBR (english full)。"""
    found = {}
    for p in paras:
        text = p.get("text", "")
        for m in PAT_ZH_EN_ABBR.finditer(text):
            zh, en, abbr = clean_zh_term(m.group(1)), m.group(2).strip(), m.group(3)
            if len(zh) < 2:
                continue
            if abbr is None and re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", en):
                abbr, en = en, None   # 括号内只有缩写：中文（EIS）
            key = normalize(zh)
            e = found.setdefault(key, {"term": zh, "definition": en, "abbr": abbr,
                                       "definition_pid": p["pid"], "pids": [], "count": 0,
                                       "source": "abbr_definition"})
            if e["definition_pid"] != p["pid"] and abbr and not e.get("abbr"):
                e["abbr"] = abbr  # 后出现的定义里补缩写
                e.setdefault("conflict_note", "缩写定义出现于多处")
            e["pids"].append(p["pid"]); e["count"] += 1
        for m in PAT_ABBR_EN.finditer(text):
            abbr, en = m.group(1), m.group(2).strip()
            if len(en.split()) < 1:
                continue
            key = normalize(abbr)
            e = found.setdefault(key, {"term": abbr, "definition": en, "abbr": abbr,
                                       "definition_pid": p["pid"], "pids": [], "count": 0,
                                       "source": "abbr_definition"})
            e["pids"].append(p["pid"]); e["count"] += 1
    # 统计各形式在全文的出现 pids
    out = []
    for e in found.values():
        forms = {f for f in (e["term"], e.get("abbr"), e.get("definition")) if f}
        pids, total = [], 0
        for q in paras:
            hits = sum(q.get("text", "").count(f) for f in forms)
            if hits:
                pids.append(q["pid"]); total += hits
        e["pids"] = sorted(set(e["pids"]) | set(pids))
        e["count"] = total
        out.append(e)
    out.sort(key=lambda x: -x["count"])
    return out[:MAX_CANDIDATES]

def scan_quoted_terms(paras):
    """(b) 引号/书名号术语，出现 ≥2 次才收。"""
    cnt, pids = Counter(), defaultdict(list)
    for p in paras:
        for m in PAT_QUOTED.finditer(p.get("text", "")):
            term = next(g for g in m.groups() if g)
            cnt[term] += 1
            pids[term].append(p["pid"])
    out = [{"term": t, "definition": None, "abbr": None, "definition_pid": None,
            "pids": sorted(set(pids[t])), "count": c, "source": "quoted"}
           for t, c in cnt.most_common() if c >= 2]
    return out[:MAX_CANDIDATES]

def scan_hfreq(paras):
    """(c) 高频复合词：≥4 字中文词组或 ≥2 词英文短语，出现 ≥3 次。"""
    zh_cnt, en_cnt = Counter(), Counter()
    zh_pids, en_pids = defaultdict(set), defaultdict(set)
    for p in paras:
        text = p.get("text", "")
        for run in ZH_RUN.findall(text):
            seen = set()
            for n in range(ZH_NGRAM_RANGE[0], min(ZH_NGRAM_RANGE[1], len(run)) + 1):
                for i in range(len(run) - n + 1):
                    ng = run[i:i + n]
                    if ng not in seen:
                        seen.add(ng); zh_cnt[ng] += 1; zh_pids[ng].add(p["pid"])
        words = [w for w in EN_WORD.findall(text) if w.lower() not in EN_STOP and len(w) > 2]
        for n in range(EN_PHRASE_RANGE[0], EN_PHRASE_RANGE[1] + 1):
            for i in range(len(words) - n + 1):
                ph = " ".join(words[i:i + n])
                en_cnt[ph] += 1; en_pids[ph].add(p["pid"])
    def keep_longest(cnt):
        keep = {}
        for t, c in cnt.items():
            if c < HFREQ_MIN_COUNT:
                continue
            keep[t] = c
        # 去掉被更长且同频（±0）词组包含的短词组
        dropped = set()
        for t in sorted(keep, key=len):
            for u in list(keep):
                if len(u) > len(t) and t in u and keep[u] >= keep[t]:
                    dropped.add(t); break
        return {t: c for t, c in keep.items() if t not in dropped}
    out = []
    for cnt, pidmap, lang in ((keep_longest(zh_cnt), zh_pids, "zh"),
                              (keep_longest(en_cnt), en_pids, "en")):
        for t, c in sorted(cnt.items(), key=lambda x: -x[1]):
            out.append({"term": t, "definition": None, "abbr": None, "definition_pid": None,
                        "pids": sorted(pidmap[t]), "count": c, "source": f"hfreq_{lang}"})
    out.sort(key=lambda x: -x["count"])
    return out[:MAX_CANDIDATES]

# ---------------- 2. 交叉引用一致性 ----------------
def xref_target_key(kind, target):
    return f"{kind}:{target.replace('.', '-').replace('–', '-')}"

def audit_xrefs(chapters):
    paras = chapters.get("paragraphs", [])
    defs, refs = {}, []   # defs: key -> {raw,pid,kind,target,file}
    sec_file = {s["sid"]: s.get("file_key") for s in chapters.get("sections", [])}
    for p in paras:
        pid, kind, text = p["pid"], p.get("kind"), p.get("text", "")
        fkey = sec_file.get(re.match(r"(C\d+-S\d+)", pid).group(1), "?")
        if kind in DEF_KINDS:
            for rx, k in ((FIG_DEF, "figure"), (TAB_DEF, "table"), (EQ_DEF, "equation")):
                m = rx.match(text.strip())
                if m:
                    key = xref_target_key(k, m.group(2))
                    defs.setdefault(key, {"raw": m.group(0), "pid": pid, "kind": k,
                                          "target": m.group(2), "file": fkey})
    def_keys = set(defs)
    for p in paras:
        for x in p.get("xrefs", []):
            if x["kind"] not in ("figure", "table", "equation"):
                continue
            key = xref_target_key(x["kind"], x["target"])
            d = defs.get(key)
            if d and d["pid"] == p["pid"]:
                continue  # 定义段自身
            refs.append({"raw": x["raw"], "pid": p["pid"], "kind": x["kind"],
                         "target": x["target"], "resolved": key in def_keys})
    dangling = [r for r in refs if not r["resolved"]]
    ref_keys = {xref_target_key(r["kind"], r["target"]) for r in refs}
    unreferenced = [d for k, d in defs.items() if k not in ref_keys]
    # 编号连续性：同章（file）同 kind，按文档序编号应非降
    numbering = []
    seq = defaultdict(list)   # (file, kind) -> [(numtuple, pid)]
    for p in paras:
        if p.get("kind") not in DEF_KINDS:
            continue
        fkey = sec_file.get(re.match(r"(C\d+-S\d+)", p["pid"]).group(1), "?")
        for rx, k in ((FIG_DEF, "figure"), (TAB_DEF, "table"), (EQ_DEF, "equation")):
            m = rx.match(p.get("text", "").strip())
            if m:
                nums = tuple(int(x) for x in re.split(r"[-–.]", m.group(2)) if x.isdigit())
                seq[(fkey, k)].append((nums, p["pid"]))
    for (fkey, k), items in seq.items():
        for (prev, _pid1), (cur, pid2) in zip(items, items[1:]):
            if cur <= prev:
                numbering.append({"file": fkey, "kind": k, "issue": "编号未递增或重复",
                                  "prev": "-".join(map(str, prev)),
                                  "current": "-".join(map(str, cur)), "pid": pid2})
    return {"dangling": [{k: r[k] for k in ("raw", "pid", "kind", "target")} for r in dangling],
            "unreferenced": unreferenced,
            "numbering": numbering,
            "n_definitions": len(defs), "n_refs": len(refs)}

# ---------------- 3. 结论句矛盾候选 ----------------
def conclusion_sentences(paras):
    sents = []
    for p in paras:
        if p.get("kind") != "body":
            continue
        fkey = re.match(r"(C\d+)", p["pid"]).group(1)
        for s in SENT_SPLIT.split(p.get("text", "")):
            s = s.strip()
            if len(s) < 8:
                continue
            low = s.lower()
            if any(w in s or w in low for w in CONCL_WORDS):
                sents.append({"pid": p["pid"], "chapter": fkey, "sentence": s})
    return sents

def subject_ngrams(sentence):
    """结论句主语 n-gram：中文里"表明/综上"等词既可能跟在主语后，也可能引出宾语从句
    （主语在关键词之后），故取关键词两侧文本（去掉关键词本身与语气词）的并集。"""
    text = sentence
    for w in CONCL_WORDS:
        text = re.sub(re.escape(w), " ", text, flags=re.I)
    for w in ("本文", "本研究", "我们", "实验", "结果将", "结果", "由此", "因此", "可以"):
        text = text.replace(w, " ")
    grams = set()
    for run in ZH_RUN.findall(text):
        grams.update(run[i:i + 3] for i in range(len(run) - 2))
    grams.update(w.lower() for w in EN_WORD.findall(text) if len(w) > 2)
    return grams or {sentence[:6]}

def polarity(sentence):
    low = sentence.lower()
    neg = any(w in sentence or w in low for w in NEG_WORDS)
    return "negative" if neg else "positive"

def find_contradictions(chapters):
    sents = conclusion_sentences(chapters.get("paragraphs", []))
    cands = []
    grams = [subject_ngrams(s["sentence"]) for s in sents]
    pols = [polarity(s["sentence"]) for s in sents]
    for i in range(len(sents)):
        for j in range(i + 1, len(sents)):
            if sents[i]["chapter"] == sents[j]["chapter"]:
                continue  # 只跨章比对
            if pols[i] == pols[j]:
                continue
            a, b = grams[i], grams[j]
            ov = len(a & b) / max(1, min(len(a), len(b)))
            if ov >= SUBJECT_OVERLAP_MIN:
                cands.append({
                    "overlap": round(ov, 3),
                    "pair": [{"pid": sents[i]["pid"], "polarity": pols[i],
                              "sentence": sents[i]["sentence"][:200]},
                             {"pid": sents[j]["pid"], "polarity": pols[j],
                              "sentence": sents[j]["sentence"][:200]}],
                    "note": "主语重叠且极性相反，需 Agent 人工裁决（不自动判错）"})
    cands.sort(key=lambda x: -x["overlap"])
    return cands

# ---------------- scan 主流程 ----------------
def cmd_scan(args):
    chapters = load_json(args.chapters)
    if not chapters:
        print(f"[scan] 无法读取 {args.chapters}", file=sys.stderr)
        return 1
    paras = body_paragraphs(chapters)
    glossary = scan_abbr_definitions(paras) + scan_quoted_terms(paras) + scan_hfreq(paras)
    dump_json(os.path.join(args.work, "glossary_candidates.json"), glossary)
    audit = audit_xrefs(chapters)
    dump_json(os.path.join(args.work, "xref_audit.json"), audit)
    contra = find_contradictions(chapters)
    dump_json(os.path.join(args.work, "contradiction_candidates.json"), contra)
    print(f"[scan] 术语候选 {len(glossary)} 条 | dangling {len(audit['dangling'])} / "
          f"unreferenced {len(audit['unreferenced'])} / 编号问题 {len(audit['numbering'])} | "
          f"矛盾候选 {len(contra)} 对")
    if audit["dangling"]:
        print("[scan][WARN] 存在悬空交叉引用，validate_output 将 FAIL：修复引用或如实降级 status",
              file=sys.stderr)
    return 0

# ---------------- 4. 术语表与异写报告 ----------------
def parse_glossary_md(path):
    """从 glossary.md 恢复术语条目（impact 子命令用，避免再依赖 review 文件）。"""
    terms = []
    if not path or not os.path.exists(path):
        return terms
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("|") or "---" in line or "规范写法" in line:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0]:
                variants = [v.strip() for v in re.split(r"[,，、]", cells[1]) if v.strip()]
                terms.append({"canonical": cells[0], "variants": variants})
    return terms

def cmd_glossary(args):
    chapters = load_json(args.chapters)
    review = load_json(args.review)
    if chapters is None:
        print(f"[glossary] 无法读取 {args.chapters}", file=sys.stderr)
        return 1
    if not isinstance(review, list):
        print(f"[glossary] glossary_review.json 缺失或不是列表: {args.review}", file=sys.stderr)
        return 1
    paras = body_paragraphs(chapters)
    kept = [r for r in review if r.get("keep", True) and r.get("canonical")]

    lines = ["# 术语表（由 glossary_review.json 审定生成）", "",
             "| 规范写法 (canonical) | 认可的异写/缩写 | 定义位置 (pid) |", "|---|---|---|"]
    for r in kept:
        variants = "，".join(r.get("variants") or [])
        lines.append(f"| {r['canonical']} | {variants} | {r.get('definition_pid') or '—'} |")
    with open(os.path.join(args.work, "glossary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # 同概念异写逐处检测 + 符号冲突
    terms_report, conflicts = [], []
    canon_norms = {}
    abbr_owner = {}
    for r in kept:
        canon = r["canonical"]
        cn = normalize(canon)
        if cn in canon_norms and canon_norms[cn]["definition_pid"] != r.get("definition_pid"):
            if r.get("definition_pid") and canon_norms[cn].get("definition_pid"):
                conflicts.append({"type": "double_definition", "canonical": canon,
                                  "definition_pids": [canon_norms[cn]["definition_pid"],
                                                      r["definition_pid"]]})
        canon_norms.setdefault(cn, r)
        forms = {canon} | set(r.get("variants") or [])
        for v in forms:
            nv = normalize(v)
            if re.fullmatch(r"[A-Z][A-Za-z0-9]{1,9}", v):
                if nv in abbr_owner and abbr_owner[nv] != canon:
                    conflicts.append({"type": "symbol_clash", "symbol": v,
                                      "meanings": [abbr_owner[nv], canon]})
                abbr_owner.setdefault(nv, canon)
        occ, non_canon = 0, []
        for p in paras:
            text = p.get("text", "")
            # 定义处豁免：definition_pid 段落中"中文（english, ABBR）"整体不计入异写统计
            exempt = []
            if r.get("definition_pid") == p["pid"]:
                for rx in (PAT_ZH_EN_ABBR, PAT_ABBR_EN):
                    exempt += [(m.start(), m.end()) for m in rx.finditer(text)]
            # 重叠命中只计最长写法（"两步烧结工艺"内的"两步烧结"不重复计数）
            raw_hits = []
            for v in sorted(forms, key=len, reverse=True):
                start = 0
                while True:
                    i = text.find(v, start)
                    if i < 0:
                        break
                    raw_hits.append((i, i + len(v), v))
                    start = i + len(v)
            hits = []
            for a, b, v in raw_hits:
                if any(x <= a and b <= y for x, y, _ in hits):
                    continue
                hits.append((a, b, v))
            for i, j, v in hits:
                if any(a <= i < b for a, b in exempt):
                    continue
                occ += 1
                if normalize(v) != cn:
                    non_canon.append({"pid": p["pid"], "variant": v,
                                      "text": text[max(0, i - 20):j + 20]})
        terms_report.append({"canonical": canon, "variants": sorted(forms - {canon}),
                             "definition_pid": r.get("definition_pid"),
                             "occurrences": occ, "non_canonical": non_canon,
                             "variant_rate": round(len(non_canon) / occ, 3) if occ else 0.0})
    report = {"terms": terms_report, "conflicts": conflicts,
              "summary": {"n_terms": len(kept),
                          "n_noncanonical_occurrences": sum(len(t["non_canonical"]) for t in terms_report),
                          "n_conflicts": len(conflicts)}}
    dump_json(os.path.join(args.work, "consistency_report.json"), report)
    md = ["# 跨章节一致性报告", "",
          f"- 审定术语 {len(kept)} 条；异写出现 {report['summary']['n_noncanonical_occurrences']} 处；"
          f"符号/定义冲突 {len(conflicts)} 处。", ""]
    for t in terms_report:
        md.append(f"## {t['canonical']}（出现 {t['occurrences']} 次，异写率 {t['variant_rate']:.0%}）")
        if t["non_canonical"]:
            for nc in t["non_canonical"][:50]:
                md.append(f"- [{nc['pid']}] 写作「{nc['variant']}」：…{nc['text']}…")
        else:
            md.append("- 未发现异写。")
        md.append("")
    if conflicts:
        md.append("## 符号/定义冲突")
        for c in conflicts:
            md.append(f"- `{c['type']}`: {json.dumps(c, ensure_ascii=False)}")
    with open(os.path.join(args.work, "consistency_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"[glossary] 术语表 {len(kept)} 条 | 异写 {report['summary']['n_noncanonical_occurrences']} 处 | "
          f"冲突 {len(conflicts)} 处 -> glossary.md / consistency_report.{{json,md}}")
    return 0

# ---------------- 5. 影响面分析 ----------------
def cmd_impact(args):
    chapters = load_json(args.chapters)
    if not chapters:
        print(f"[impact] 无法读取 {args.chapters}", file=sys.stderr)
        return 1
    paras = body_paragraphs(chapters)
    sec_file = {s["sid"]: s.get("file_key") for s in chapters.get("sections", [])}
    impacted = {}   # pid -> {pid, reasons[], snippet}

    def add(pid, reason, snippet=""):
        e = impacted.setdefault(pid, {"pid": pid, "reasons": [], "snippet": snippet[:120]})
        if reason not in e["reasons"]:
            e["reasons"].append(reason)

    if args.changed_term:
        term = args.changed_term
        forms = {term}
        for t in parse_glossary_md(args.glossary):
            if t["canonical"] == term or term in t["variants"]:
                forms |= {t["canonical"]} | set(t["variants"])
        for p in paras:
            text = p.get("text", "")
            hit = [f for f in forms if f and f in text]
            if hit:
                add(p["pid"], f"引用术语（命中写法: {'/'.join(hit[:3])}）", text)
        # 结论句重叠：受术语影响段落的结论句主语与其他段结论句重叠
        sents = conclusion_sentences(chapters.get("paragraphs", []))
        hit_pids = set(impacted)
        hit_grams = [subject_ngrams(s["sentence"]) for s in sents if s["pid"] in hit_pids]
        for s in sents:
            if s["pid"] in hit_pids:
                continue
            g = subject_ngrams(s["sentence"])
            for hg in hit_grams:
                if len(g & hg) / max(1, min(len(g), len(hg))) >= SUBJECT_OVERLAP_MIN:
                    add(s["pid"], "结论句主语与受影响段落重叠", s["sentence"])
                    break
    elif args.changed_sid:
        sid = args.changed_sid
        ch = re.match(r"(C\d+)", sid)
        changed_file = sec_file.get(sid, ch.group(1) if ch else sid)
        for p in paras:
            if p["pid"].startswith(sid + "-P"):
                add(p["pid"], "属于被修改的章节", p.get("text", ""))
        # xref 指向该章（第X章/第X节）或指向该章内图表
        def_keys_in_file = {k for k, d in _defs_iter(chapters) if d["file"] == changed_file}
        # 章节标题编号 → 文件映射（"第3章"/"3.2 节"指向 changed_file 的标题）
        nums_in_file = {h.get("number") for h in chapters.get("headings", [])
                        if h.get("file_key") == changed_file and h.get("number")}
        cn_num = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
                  "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}
        for p in paras:
            if p["pid"].startswith(sid):
                continue
            for x in p.get("xrefs", []):
                if x["kind"] in ("chapter", "section"):
                    tgt = cn_num.get(x["target"], x["target"])
                    if any(n == tgt or (n or "").startswith(tgt + ".") for n in nums_in_file):
                        add(p["pid"], f"引用被修改章节（{x['raw']}）", p.get("text", ""))
                    continue
                key = xref_target_key(x["kind"], x["target"])
                if key in def_keys_in_file:
                    add(p["pid"], f"交叉引用指向被修改章节的{x['kind']} {x['target']}",
                        p.get("text", ""))
        # 结论句重叠
        sents = conclusion_sentences(chapters.get("paragraphs", []))
        in_sents = [s for s in sents if s["pid"].startswith(sid)]
        out_sents = [s for s in sents if not s["pid"].startswith(sid)]
        for os_ in out_sents:
            og = subject_ngrams(os_["sentence"])
            for is_ in in_sents:
                ig = subject_ngrams(is_["sentence"])
                if len(og & ig) / max(1, min(len(og), len(ig))) >= SUBJECT_OVERLAP_MIN:
                    add(os_["pid"], "结论句主语与被修改章节结论句重叠", os_["sentence"])
                    break
    else:
        print("[impact] 需要 --changed-term 或 --changed-sid 之一", file=sys.stderr)
        return 1

    items = sorted(impacted.values(), key=lambda e: e["pid"])
    report = {"changed_term": args.changed_term, "changed_sid": args.changed_sid,
              "n_impacted": len(items), "impacted": items}
    dump_json(os.path.join(args.work, "impact_report.json"), report)
    md = [f"# 影响面分析：{args.changed_term or args.changed_sid}", "",
          f"受影响段落 {len(items)} 个：", ""]
    for e in items:
        md.append(f"- **{e['pid']}** — {'；'.join(e['reasons'])}")
        if e["snippet"]:
            md.append(f"  > {e['snippet']}")
    with open(os.path.join(args.work, "impact_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"[impact] {args.changed_term or args.changed_sid} -> 受影响段落 {len(items)} 个 "
          f"-> impact_report.{{json,md}}")
    return 0

def _defs_iter(chapters):
    audit = None
    paras = chapters.get("paragraphs", [])
    sec_file = {s["sid"]: s.get("file_key") for s in chapters.get("sections", [])}
    for p in paras:
        if p.get("kind") not in DEF_KINDS:
            continue
        fkey = sec_file.get(re.match(r"(C\d+-S\d+)", p["pid"]).group(1), "?")
        for rx, k in ((FIG_DEF, "figure"), (TAB_DEF, "table"), (EQ_DEF, "equation")):
            m = rx.match(p.get("text", "").strip())
            if m:
                yield xref_target_key(k, m.group(2)), {"raw": m.group(0), "pid": p["pid"],
                                                       "kind": k, "target": m.group(2),
                                                       "file": fkey}

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("scan", "glossary", "impact"):
        sp = sub.add_parser(name)
        sp.add_argument("--chapters", required=True)
        sp.add_argument("--work", default="/app/work")
        if name == "glossary":
            sp.add_argument("--review", required=True)
        if name == "impact":
            sp.add_argument("--glossary", default=None)
            sp.add_argument("--changed-term", default=None)
            sp.add_argument("--changed-sid", default=None)
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    return {"scan": cmd_scan, "glossary": cmd_glossary, "impact": cmd_impact}[args.cmd](args)

if __name__ == "__main__":
    sys.exit(main())
