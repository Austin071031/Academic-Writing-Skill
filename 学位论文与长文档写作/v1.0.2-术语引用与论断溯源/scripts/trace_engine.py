#!/usr/bin/env python3
"""trace_engine.py — 术语引用与论断溯源引擎（纯 Python3 标准库，确定性）。

子命令:
  bind       --chapters work/chapters.json --library work/library.json --work /app/work
               把每条含引用标记的段落抽为论断记录并解析到文献条目，
               输出 work/claim_bindings.json（status: bound / partially_bound / unbound）。
  verify     --chapters work/chapters.json --library work/library.json
               --materials <合并材料文本> --work /app/work
               输出 work/citation_audit.json / .md：
               (a) 引用存在性（unbound 清单, critical）
               (b) 论断-材料数值一致性（verbatim / derived ±1% 含百分比换算 / unverified）
               (c) 语气边界（升格 overstated / 否定翻转 negation_flip 候选）
               (d) 漏引（含未溯源事实数值但无引用标记的段落 → 推荐 top3 候选条目）
  render_refs --library work/library.json [--order work/order.json]
               [--style gbt2015_numeric] --work /app/work
               调用 cite_engine.py render 生成 work/references.md（GB/T 7714-2015 顺序编码），
               并交叉核对正文引用编号连续、双向一致 → work/references_audit.json。
  annotate   --chapter <稿件> --audit work/citation_audit.json --work /app/work
               在存疑引用处加 ⚠ 批注（不改正文），输出 work/annotated_draft.md。

退出码: bind/verify 发现 unbound（critical）时返回 1，其余 0；参数错误 2。
判据详见 references/citation_rules.md。
"""
import argparse, json, os, re, subprocess, sys

# ---------------------------------------------------------------- 通用工具

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CITE_ENGINE = os.path.join(SCRIPT_DIR, "cite_engine.py")

SENT_SPLIT = re.compile(r"(?<=[。！？；!?])\s*|\n+")

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def dump_json(obj, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def split_sentences(text):
    """按中英文句末标点与换行切句，保留非空句。"""
    parts = SENT_SPLIT.split(text)
    out = []
    for p in parts:
        p = p.strip()
        if p:
            out.append(p)
    return out

# ---------------------------------------------------------------- 数值抽取（带遮蔽）

MASK_PATTERNS = [
    re.compile(r"第[一二三四五六七八九十百\d]+[章节卷篇]"),        # 章节编号
    re.compile(r"[图表式]\s*\d+(?:[-–.]\d+)*"),                     # 图3-1 / 表2 / 式3
    re.compile(r"(?:Fig(?:ure)?|Table|Eq(?:uation)?)\.?\s*\d+(?:[-–.]\d+)*", re.I),
    re.compile(r"\d+(?:\.\d+){2,}"),                                # 多级编号 3.1.2
    re.compile(r"(?:19|20)\d{2}[a-z]?"),                            # 年份
    re.compile(r"\[[^\]]{0,40}\]"),                                 # 引用标记 [1] [1-3] [^a]
    re.compile(r"\\cite[a-z]*\{[^}]*\}"),                           # LaTeX 引用
    re.compile(r"https?://\S+|doi\s*[:：]?\s*\S+", re.I),           # URL/DOI
]
# 数字：前面不能是字母/数字/点（遮蔽 Li6PS5Cl、B7），后面不能接数字或点（允许单位字母）
NUM_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\d.])")

def mask_text(text):
    """遮蔽图表/章节编号、年份、引用标记等，返回 (遮蔽后文本, )。"""
    t = text
    for pat in MASK_PATTERNS:
        t = pat.sub(" ", t)
    return t

def extract_numbers(text):
    """抽取事实数值（float 列表，去重保留出现顺序）。"""
    t = mask_text(text)
    vals = []
    for m in NUM_RE.finditer(t):
        try:
            v = float(m.group(0))
        except ValueError:
            continue
        vals.append(v)
    # 去重保序
    seen, out = set(), []
    for v in vals:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out

# ---------------------------------------------------------------- 数值核对

def close(a, b, rel=0.01):
    """|a-b| <= rel*|b|（b=0 时要求 a 也为 0）。"""
    if b == 0:
        return a == 0
    return abs(a - b) <= rel * abs(b)

def classify_number(v, pool, pair_pool):
    """返回 (verdict, evidence)。
    verbatim: 材料中精确出现（容差 1e-6 相对）
    derived:  ±1% 内匹配材料单值、百分比换算（×/÷100）、或材料两值四则结果
    unverified: 其余
    """
    for b in pool:
        if b != 0 and abs(v - b) <= 1e-6 * max(abs(b), 1e-12) or v == b:
            return "verbatim", f"材料含相同数值 {b:g}"
    for b in pool:
        if close(v, b):
            return "derived", f"与材料数值 {b:g} 偏差 ≤1%"
    # 百分比换算：40 <-> 0.4
    for b in pool:
        if close(v, b * 100) or close(v, b / 100):
            return "derived", f"与材料数值 {b:g} 为百分比换算关系（±1%）"
    # 四则（池较大时跳过，防组合爆炸与误命中）
    if pair_pool:
        for x in pair_pool:
            for y in pair_pool:
                for r, op in ((x + y, "+"), (x - y, "-"), (x * y, "*"),
                              (x / y if y else None, "/")):
                    if r is not None and close(v, r):
                        return "derived", f"≈材料数值 {x:g}{op}{y:g}={r:g}（±1%）"
    return "unverified", "材料中未找到该数值或可推导关系"

# ---------------------------------------------------------------- 语气强度

TONE_LADDER = [
    (4, re.compile(r"证明|证实|完全解决|彻底解决|从根本上解决|proven?|confirm", re.I)),
    (3, re.compile(r"表明|说明|demonstrate|shows?\b|revealed?", re.I)),
    (2, re.compile(r"显示|暗示|indicate|imply|implied", re.I)),
    (1, re.compile(r"可能|有望|或可以|潜在|may\b|might\b|could\b|suggest", re.I)),
]
NEUTRAL_LEVEL = 3  # 材料/论断中无语气词的直接陈述视为平实断言（与“表明”同级）

def tone_level(sentence):
    best = 0
    for lv, pat in TONE_LADDER:
        if pat.search(sentence):
            best = max(best, lv)
    return best or NEUTRAL_LEVEL

NEG_CLAIM = re.compile(r"(?:完全|彻底|根本)?(?:解决|克服|消除|攻克)s?|solved|overcome|eliminate", re.I)
NEG_MATERIAL = re.compile(r"挑战|困难|问题|瓶颈|尚未|仍未|仍然|受限|challenge|problem|difficult|"
                          r"remain|bottleneck|not\s+(?:yet\s+)?(?:solved|resolved)", re.I)

# ---------------------------------------------------------------- 关键词重叠

STOP = set("的 了 与 和 是 在 对 为 及 等 中 上 下 其 该 本 通过 进行 研究 方法 结果 "
           "the a an of and in on for to with by is are was were from as at".split())

def tokens(text):
    """拉丁词（len≥3 小写）+ CJK 二元组。"""
    toks = set(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text))
    toks -= STOP
    cjk = re.findall(r"[\u4e00-\u9fff]+", text)
    for seg in cjk:
        for i in range(len(seg) - 1):
            toks.add(seg[i:i + 2])
    return toks

# ---------------------------------------------------------------- 作者/年份规范化

COMPOUND_ZH_SURNAME = ("欧阳", "司马", "诸葛", "上官", "夏侯", "皇甫", "尉迟", "公孙",
                       "令狐", "宇文", "长孙", "慕容", "司徒", "司空")

def norm_surname(name):
    """作者姓名 → 规范化姓（小写去点号去空格）。中文取姓；西文取逗号前或末词。"""
    if not name:
        return ""
    n = name.strip()
    n = re.sub(r"(?i)\s*(et\s*al\.?|等)\s*$", "", n).strip()  # 先剥离等/et al 再判断语种
    if re.search(r"[\u4e00-\u9fff]", n):
        for cs in COMPOUND_ZH_SURNAME:
            if n.startswith(cs):
                return cs
        return n[:1]
    if "," in n:
        n = n.split(",", 1)[0]
    else:
        parts = n.split()
        n = parts[-1] if parts else n
    return re.sub(r"[.\s\-]", "", n).lower()

def norm_year(y):
    m = re.search(r"(19|20)\d{2}", str(y or ""))
    return m.group(0) if m else ""

# ---------------------------------------------------------------- 文献条目索引

def build_indexes(records):
    by_key, by_author_year = {}, {}
    for i, r in enumerate(records):
        rid = r["id"]
        key = (r.get("key") or "").strip()
        if key:
            by_key[key.lower()] = rid
        year = norm_year(r.get("year"))
        surnames = set()
        for a in r.get("authors") or []:
            sn = norm_surname(a)
            if sn:
                surnames.add(sn)
        if year and surnames:
            by_author_year.setdefault((year, frozenset(surnames)), []).append(rid)
    return by_key, by_author_year

def match_author_year(mark_author, mark_year, records):
    """author_year 标记 → entry_id 列表（作者姓规范化 + 年份精确）。"""
    my = norm_year(mark_year)
    ma = norm_surname(mark_author)
    if not my or not ma:
        return []
    hits = []
    for r in records:
        if norm_year(r.get("year")) != my:
            continue
        for a in r.get("authors") or []:
            if norm_surname(a) == ma:
                hits.append(r["id"])
                break
    return hits

# ---------------------------------------------------------------- bind

def claim_sentences(p):
    """取段落中包含引用标记的句子（无标记句则整段）。"""
    text = p.get("text", "")
    marks = p.get("cite_marks") or []
    if not marks:
        return text.strip()
    picked = []
    for s in split_sentences(text):
        start = text.find(s)
        if start < 0:
            continue
        end = start + len(s)
        if any(not (m["span"][1] <= start or m["span"][0] >= end) for m in marks):
            picked.append(s)
    return " ".join(picked) if picked else text.strip()

def resolve_marks(p, records, by_key):
    """解析段落全部引用标记 → (entry_ids, unresolved_descriptions)。"""
    n = len(records)
    entry_ids, unresolved = [], []
    for m in p.get("cite_marks") or []:
        style = m.get("style")
        if style == "numeric":
            for num in m.get("nums") or []:
                if 1 <= num <= n:
                    entry_ids.append(records[num - 1]["id"])
                else:
                    unresolved.append(f"numeric [{num}] 越界（文献表仅 {n} 条）")
        elif style == "author_year":
            hits = match_author_year(m.get("author", ""), m.get("year", ""), records)
            if hits:
                entry_ids.extend(hits)
            else:
                unresolved.append(f"author_year {m.get('raw')} 未匹配到文献条目")
        elif style == "latex":
            for k in m.get("keys") or []:
                rid = by_key.get(k.lower())
                if rid:
                    entry_ids.append(rid)
                else:
                    unresolved.append(f"latex key '{k}' 在文献库中不存在")
        elif style == "footnote_md":
            label = (m.get("label") or "").lower()
            rid = by_key.get(label)
            if rid:
                entry_ids.append(rid)
            else:
                unresolved.append(f"footnote [^{m.get('label')}] 未匹配到文献条目")
    # 去重保序
    seen, uniq = set(), []
    for e in entry_ids:
        if e not in seen:
            seen.add(e)
            uniq.append(e)
    return uniq, unresolved

def do_bind(chapters, library):
    records = library.get("records", [])
    by_key, _ = build_indexes(records)
    claims = []
    idx = 0
    for p in chapters.get("paragraphs", []):
        if p.get("kind") in ("reference_list", "heading", "caption"):
            continue
        marks = p.get("cite_marks") or []
        if not marks:
            continue
        idx += 1
        entry_ids, unresolved = resolve_marks(p, records, by_key)
        n_marks = len(marks)
        if entry_ids and not unresolved:
            status = "bound"
        elif entry_ids:
            status = "partially_bound"
        else:
            status = "unbound"
        claims.append({
            "claim_id": f"CLM{idx:03d}",
            "pid": p["pid"],
            "sentence": claim_sentences(p),
            "cite_marks": marks,
            "entry_ids": entry_ids,
            "unresolved": unresolved,
            "n_marks": n_marks,
            "status": status,
        })
    stats = {
        "n_claims": len(claims),
        "bound": sum(1 for c in claims if c["status"] == "bound"),
        "partially_bound": sum(1 for c in claims if c["status"] == "partially_bound"),
        "unbound": sum(1 for c in claims if c["status"] == "unbound"),
        "n_records": len(records),
    }
    return {"claims": claims, "stats": stats}

def cmd_bind(args):
    chapters = load_json(args.chapters)
    library = load_json(args.library)
    if chapters is None or library is None:
        print("[bind] chapters/library 不可解析", file=sys.stderr)
        return 2
    out = do_bind(chapters, library)
    dump_json(out, os.path.join(args.work, "claim_bindings.json"))
    s = out["stats"]
    print(f"[bind] 论断 {s['n_claims']} 条: bound={s['bound']} "
          f"partially_bound={s['partially_bound']} unbound={s['unbound']}")
    for c in out["claims"]:
        if c["status"] != "bound":
            print(f"  [{c['status']}] {c['pid']}: {'; '.join(c['unresolved'])}")
    return 1 if s["unbound"] else 0

# ---------------------------------------------------------------- verify

INTENT_WORDS = re.compile(r"目标|拟在|旨在|计划|试图|期望|预期|下一步|将开展|"
                          r"target|aim to|plan to|expected to", re.I)
CITE_WORTHY = re.compile(r"已有研究|据报道|文献|研究表明|业界|学界|此前|前人|"
                         r"studies|reported|literature|previous", re.I)

def best_material_sentence(claim_sent, mat_sents):
    """按关键词重叠 + 数值重合挑选与论断句最相关的材料句。"""
    ct = tokens(claim_sent)
    cnums = set(extract_numbers(claim_sent))
    best, best_score = None, 0
    for s in mat_sents:
        st = tokens(s)
        score = len(ct & st)
        score += 3 * len(cnums & set(extract_numbers(s)))
        if score > best_score:
            best, best_score = s, score
    if best is not None and best_score >= 2:
        return best, best_score
    return None, 0

def do_verify(chapters, library, materials_text):
    records = library.get("records", [])
    bindings = do_bind(chapters, library)
    claims = bindings["claims"]

    mat_numbers = extract_numbers(materials_text)
    pair_pool = mat_numbers if len(mat_numbers) <= 60 else []
    mat_sents = split_sentences(materials_text)

    audit = {"unbound": [], "numeric": [], "tone": [], "missing_citation": [],
             "stats": {}}

    # (a) 引用存在性
    for c in claims:
        if c["status"] == "unbound":
            audit["unbound"].append({
                "claim_id": c["claim_id"], "pid": c["pid"],
                "sentence": c["sentence"],
                "detail": "; ".join(c["unresolved"]) or "全部引用标记未命中文献库",
                "severity": "critical",
                "note": "疑似引用了不存在的文献，须由 Agent 裁决（删除/替换/补录条目）",
            })
        elif c["status"] == "partially_bound":
            audit["unbound"].append({
                "claim_id": c["claim_id"], "pid": c["pid"],
                "sentence": c["sentence"],
                "detail": "; ".join(c["unresolved"]),
                "severity": "critical",
                "note": "部分引用标记未命中文献库",
            })

    # (b) 论断-材料数值一致性 + (c) 语气边界
    n_verbatim = n_derived = n_unverified = 0
    for c in claims:
        sent = c["sentence"]
        if INTENT_WORDS.search(sent):
            continue  # 研究目标/预期数值非事实论断
        for v in extract_numbers(sent):
            verdict, ev = classify_number(v, mat_numbers, pair_pool)
            rec = {"claim_id": c["claim_id"], "pid": c["pid"], "value": f"{v:g}",
                   "verdict": verdict, "evidence": ev, "sentence": sent}
            audit["numeric"].append(rec)
            if verdict == "verbatim":
                n_verbatim += 1
            elif verdict == "derived":
                n_derived += 1
            else:
                n_unverified += 1
        # 语气边界：逐句评估（同一段落不同句可能对应不同材料句）
        for s_i in split_sentences(sent):
            if INTENT_WORDS.search(s_i):
                continue
            ms, score = best_material_sentence(s_i, mat_sents)
            if not ms:
                continue
            cl, ml = tone_level(s_i), tone_level(ms)
            issue = None
            # 升格：仅当论文达到"证明/彻底解决"级(L4)且材料为或然/显示级(≤L2)
            if cl >= 4 and cl - ml >= 2:
                issue = "overstated"
            if NEG_CLAIM.search(s_i) and NEG_MATERIAL.search(ms):
                issue = "negation_flip" if issue is None else issue + "+negation_flip"
            if issue:
                audit["tone"].append({
                    "claim_id": c["claim_id"], "pid": c["pid"], "sentence": s_i,
                    "issue": issue, "claim_tone_level": cl, "material_tone_level": ml,
                    "material_sentence": ms,
                    "note": "语气升格/否定翻转候选，供 Agent 对照原文裁决，引擎不自动改写",
                })

    # (d) 漏引：含未溯源事实数值或引述型表述但无引用标记的正文段
    for p in chapters.get("paragraphs", []):
        if p.get("kind") in ("reference_list", "heading", "caption"):
            continue
        if p.get("cite_marks"):
            continue
        text = p.get("text", "")
        if INTENT_WORDS.search(text):
            continue
        nums = extract_numbers(text)
        if not nums:
            continue
        unverified_here = [v for v in nums
                           if classify_number(v, mat_numbers, pair_pool)[0] == "unverified"]
        if not unverified_here and not CITE_WORTHY.search(text):
            continue  # 数值均可溯源到材料（如本实验方法参数），不视为漏引
        # 推荐候选条目 top3
        pt = tokens(text)
        scored = []
        for r in records:
            rt = tokens((r.get("title") or "") + " " + (r.get("venue") or ""))
            sc = len(pt & rt)
            if sc:
                scored.append((sc, r["id"], (r.get("title") or "")[:60]))
        scored.sort(key=lambda x: (-x[0], x[1]))
        audit["missing_citation"].append({
            "pid": p["pid"], "sentence": text[:200],
            "unverified_numbers": [f"{v:g}" for v in unverified_here],
            "cite_worthy_wording": bool(CITE_WORTHY.search(text)),
            "candidates": [{"entry_id": rid, "score": sc, "title": t}
                           for sc, rid, t in scored[:3]],
            "note": "含事实数值但无引用标记，是否补引由 Agent 裁决",
        })

    audit["stats"] = {
        "n_claims": len(claims),
        "unbound": len([u for u in audit["unbound"] if u["severity"] == "critical"]),
        "numeric_verbatim": n_verbatim, "numeric_derived": n_derived,
        "numeric_unverified": n_unverified,
        "tone_candidates": len(audit["tone"]),
        "missing_citation": len(audit["missing_citation"]),
    }
    return audit

def render_audit_md(audit):
    L = ["# 引用与论断溯源审查报告", ""]
    s = audit["stats"]
    L.append(f"- 论断（含引用标记段落）: {s['n_claims']} 条")
    L.append(f"- (a) 引用存在性问题: {s['unbound']} 处（critical）")
    L.append(f"- (b) 数值核对: verbatim={s['numeric_verbatim']} "
             f"derived={s['numeric_derived']} unverified={s['numeric_unverified']}")
    L.append(f"- (c) 语气边界候选: {s['tone_candidates']} 处")
    L.append(f"- (d) 漏引候选: {s['missing_citation']} 段")
    L.append("")
    L.append("## (a) 引用存在性（critical）")
    if audit["unbound"]:
        for u in audit["unbound"]:
            L.append(f"- ⚠ [{u['pid']}] {u['detail']}")
            L.append(f"  - 论断: {u['sentence'][:120]}")
    else:
        L.append("- 无")
    L.append("")
    L.append("## (b) 论断-材料数值一致性")
    unv = [r for r in audit["numeric"] if r["verdict"] == "unverified"]
    if unv:
        for r in unv:
            L.append(f"- ⚠ [{r['pid']}] 数值 {r['value']} unverified：{r['evidence']}")
            L.append(f"  - 论断: {r['sentence'][:120]}")
    else:
        L.append("- 全部数值可溯源（verbatim/derived）")
    L.append("")
    L.append("## (c) 语气边界候选（供 Agent 裁决）")
    if audit["tone"]:
        for t in audit["tone"]:
            L.append(f"- ⚠ [{t['pid']}] {t['issue']}: 论文语气 L{t['claim_tone_level']} "
                     f"vs 材料语气 L{t['material_tone_level']}")
            L.append(f"  - 论断: {t['sentence'][:120]}")
            L.append(f"  - 材料: {t['material_sentence'][:120]}")
    else:
        L.append("- 无")
    L.append("")
    L.append("## (d) 漏引候选（供 Agent 决定是否补引）")
    if audit["missing_citation"]:
        for m in audit["missing_citation"]:
            L.append(f"- [{m['pid']}] {m['sentence'][:100]}")
            if m["unverified_numbers"]:
                L.append(f"  - 未溯源数值: {', '.join(m['unverified_numbers'])}")
            if m["candidates"]:
                cands = "; ".join(f"{c['entry_id']}({c['title']})" for c in m["candidates"])
                L.append(f"  - 推荐候选: {cands}")
            else:
                L.append("  - 推荐候选: 无（文献库中无关键词重叠条目）")
    else:
        L.append("- 无")
    L.append("")
    return "\n".join(L)

def cmd_verify(args):
    chapters = load_json(args.chapters)
    library = load_json(args.library)
    if chapters is None or library is None:
        print("[verify] chapters/library 不可解析", file=sys.stderr)
        return 2
    if not os.path.exists(args.materials):
        print(f"[verify] 材料文本不存在: {args.materials}", file=sys.stderr)
        return 2
    with open(args.materials, encoding="utf-8") as f:
        materials_text = f.read()
    audit = do_verify(chapters, library, materials_text)
    dump_json(audit, os.path.join(args.work, "citation_audit.json"))
    with open(os.path.join(args.work, "citation_audit.md"), "w", encoding="utf-8") as f:
        f.write(render_audit_md(audit))
    # 同步刷新 claim_bindings.json，保证两个产物一致
    dump_json(do_bind(chapters, library), os.path.join(args.work, "claim_bindings.json"))
    s = audit["stats"]
    print(f"[verify] unbound={s['unbound']} unverified={s['numeric_unverified']} "
          f"tone={s['tone_candidates']} missing_cite={s['missing_citation']} "
          f"-> citation_audit.json/.md")
    return 1 if s["unbound"] else 0

# ---------------------------------------------------------------- render_refs

def cmd_render_refs(args):
    library = load_json(args.library)
    if library is None:
        print("[render_refs] library 不可解析", file=sys.stderr)
        return 2
    records = library.get("records", [])
    work = args.work
    os.makedirs(work, exist_ok=True)

    order_path = args.order
    if not order_path:
        # 默认：按正文首次出现顺序（claim_bindings），未被引用的条目按库序附后
        order_path = os.path.join(work, "order.json")
        bindings = load_json(os.path.join(work, "claim_bindings.json"), {}) or {}
        seen, order = set(), []
        for c in bindings.get("claims", []):
            for e in c.get("entry_ids", []):
                if e not in seen:
                    seen.add(e)
                    order.append(e)
        for r in records:
            if r["id"] not in seen:
                order.append(r["id"])
        dump_json(order, order_path)

    ref_md = os.path.join(work, "references.md")
    r = subprocess.run([sys.executable, CITE_ENGINE, "render",
                        "--records", args.library, "--style", args.style,
                        "--order", order_path, "--out", ref_md],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        return 2

    # 交叉核对：正文引用编号 vs 文献表
    n_refs = len(load_json(order_path, []) or records)
    audit_summary = {"n_refs": n_refs, "style": args.style, "checks": {}}
    chapters_path = os.path.join(work, "chapters.json")
    rc = None
    if os.path.exists(chapters_path):
        ra = subprocess.run([sys.executable, CITE_ENGINE, "audit",
                             "--manuscript", chapters_path, "--nrefs", str(n_refs)],
                            capture_output=True, text=True)
        print(ra.stdout.strip())
        cons = load_json(os.path.join(work, "consistency_audit.json"), {}) or {}
        audit_summary["checks"] = {
            "out_of_range": cons.get("out_of_range"),
            "gaps": cons.get("gaps"),
            "sequential": cons.get("sequential"),
            "style_consistent": cons.get("style_consistent"),
        }
        rc = ra.returncode
    dump_json(audit_summary, os.path.join(work, "references_audit.json"))
    print(f"[render_refs] {n_refs} 条 -> {ref_md}（样式 {args.style}）")
    return 1 if rc else 0

# ---------------------------------------------------------------- annotate

def cmd_annotate(args):
    audit = load_json(args.audit)
    if audit is None:
        print(f"[annotate] audit 不可解析: {args.audit}", file=sys.stderr)
        return 2
    if not os.path.exists(args.chapter):
        print(f"[annotate] 稿件不存在: {args.chapter}", file=sys.stderr)
        return 2
    with open(args.chapter, encoding="utf-8") as f:
        lines = f.read().splitlines()

    notes = []  # (match_key, note_text)
    for u in audit.get("unbound", []):
        notes.append((u.get("sentence", ""), f"引用存在性: {u['detail']}（critical）"))
    for r in audit.get("numeric", []):
        if r.get("verdict") == "unverified":
            notes.append((r.get("sentence", ""),
                          f"数值 {r['value']} 未在材料中溯源（unverified）"))
    for t in audit.get("tone", []):
        notes.append((t.get("sentence", ""),
                      f"语气边界候选 {t['issue']}: 论文 L{t['claim_tone_level']} vs "
                      f"材料 L{t['material_tone_level']}，材料原句「{t['material_sentence'][:60]}」"))
    for m in audit.get("missing_citation", []):
        cands = ", ".join(c["entry_id"] for c in m.get("candidates", [])) or "无"
        notes.append((m.get("sentence", ""), f"漏引候选：推荐补引 {cands}"))

    insertions = {}  # 原始行号 -> [批注...]
    unplaced = []
    placed = 0
    for key, note in notes:
        probe = re.sub(r"\s+", "", key)[:14]
        hit = None
        if probe:
            for i, ln in enumerate(lines):
                if probe in re.sub(r"\s+", "", ln):
                    hit = i
                    break
        entry = f"> ⚠ 审校批注（trace_engine）：{note}"
        if hit is not None:
            insertions.setdefault(hit, []).append(entry)
            placed += 1
        else:
            unplaced.append(entry)
    out_lines = []
    for i, ln in enumerate(lines):
        out_lines.append(ln)
        out_lines.extend(insertions.get(i, []))  # 批注插在命中行之后，正文不改
    if unplaced:
        out_lines.append("")
        out_lines.append("## 未定位批注（引擎未能自动定位，请人工查找）")
        out_lines.extend(unplaced)
    dest = os.path.join(args.work, "annotated_draft.md")
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")
    print(f"[annotate] 批注 {len(notes)} 条（定位 {placed}，未定位 {len(unplaced)}）-> {dest}")
    return 0

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("bind")
    p.add_argument("--chapters", required=True)
    p.add_argument("--library", required=True)
    p.add_argument("--work", default="/app/work")
    p.set_defaults(fn=cmd_bind)

    p = sub.add_parser("verify")
    p.add_argument("--chapters", required=True)
    p.add_argument("--library", required=True)
    p.add_argument("--materials", required=True)
    p.add_argument("--work", default="/app/work")
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("render_refs")
    p.add_argument("--library", required=True)
    p.add_argument("--order")
    p.add_argument("--style", default="gbt2015_numeric")
    p.add_argument("--work", default="/app/work")
    p.set_defaults(fn=cmd_render_refs)

    p = sub.add_parser("annotate")
    p.add_argument("--chapter", required=True)
    p.add_argument("--audit", required=True)
    p.add_argument("--work", default="/app/work")
    p.set_defaults(fn=cmd_annotate)

    args = ap.parse_args()
    return args.fn(args)

if __name__ == "__main__":
    sys.exit(main())
