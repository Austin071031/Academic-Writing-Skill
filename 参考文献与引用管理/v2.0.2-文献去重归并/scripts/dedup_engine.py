#!/usr/bin/env python3
"""dedup_engine.py — 可解释的多信号文献去重与条目归并引擎（版本3 专属）。

设计目标：同一文献的中英文题名、预印本与正式版、期刊与会议版本、不同数据库导出
差异，都被引擎量化为成对相似信号，分三档处置（auto_merge 自动合并 /
needs_review 候选交 Agent 裁决 / protected 禁止合并保护）。每个合并决定附带
完整证据信号与理由，杜绝误合并同名作者的不同文献。

子命令:
  candidates --library work/library.json --work /app/work
      计算全部成对信号 -> work/merge_candidates.json
      （候选组清单 + 每对信号明细 + 三档分类 + 保护对清单）。
  apply --library work/library.json --decisions work/merge_decisions.jsonl \
        --work /app/work --out /app/output [--manuscript work/manuscript.json]
      读 Agent 裁决（每行 {group_id, action:"merge"|"keep_separate", keep_rid,
      drop_rids[], rationale}），执行字段择优归并 -> /app/output/library_deduped.json、
      /app/output/merge_report.md、work/merge_report.json；
      若给出 --manuscript 且其参考文献表可与条目匹配，另写 work/dedup_mapping.json
      （drop 的编号 -> keep 的编号），供后续重排。

信号定义（每对记录）:
  title_sim      0-1，题名归一化后字符 3-gram Jaccard（CJK 与 Latin 分别计算；
                 跨语言对不可比，置 0 并标 comparable=false）
  doi_match      bool，DOI 归一化后完全一致
  year_diff      int|None，年份差绝对值
  author_overlap 0-1，作者姓氏集合 Jaccard
  venue_sim      0-1，刊会名归一化字符 3-gram Jaccard
  type_compatible "same"|"preprint_formal"|"cautious"|"difficult"
                 （期刊<->预印本可合并；期刊<->会议需谨慎；其余交裁决）

三档规则:
  protected    (a) 两个不同 DOI 均存在且不相同；或
               (b) 同语种、同一第一作者、同一年、title_sim<0.60（疑似同名不同文）
  auto_merge   doi_match 为真，或 (title_sim>=0.90 且 author_overlap>=0.5 且 year_diff<=1)
  needs_review 其余具有合并潜质的对；跨语言但作者高度重合的对带
               cross_language_hint 提示（可能为同文不同译名）
"""
import argparse, json, os, re, sys, itertools, unicodedata

# ---------- 归一化 ----------

TYPE_TAG_RE = re.compile(r"\[(?:[JCMDSNRP]|EB/OL|EB|OL|A|G)\]", re.I)
REVIEW_SUFFIX_RE = re.compile(
    r"(?:^|\s)(a\s+review|review|综述|研究进展|进展|研究|overview|perspective|进展综述)[\s.。:：]*$", re.I)
ARXIV_MARK_RE = re.compile(r"arxiv(?:\s*preprint)?(?:[:\s]*\d{4}\.\d{4,5}(?:v\d+)?)?", re.I)
PUNCT_RE = re.compile(r"[\s\-–—_·,，.。:：;；!！?？'\"“”‘’()（）\[\]{}<>《》/\\|@#%&*+=~`^]+")

def normalize_title(t):
    """题名归一化：小写、去文献类型标记、去综述等价后缀、去 arXiv 标记、去标点。"""
    if not t:
        return ""
    s = unicodedata.normalize("NFKC", str(t)).lower().strip()
    s = TYPE_TAG_RE.sub(" ", s)
    s = ARXIV_MARK_RE.sub(" ", s)
    s = s.rstrip(".。")
    prev = None
    while prev != s:  # 后缀可能叠加（"...综述[ J]."）
        prev = s
        s = REVIEW_SUFFIX_RE.sub("", s).strip()
    s = PUNCT_RE.sub("", s)
    return s

def normalize_venue(v):
    if not v:
        return ""
    s = unicodedata.normalize("NFKC", str(v)).lower().strip()
    s = ARXIV_MARK_RE.sub(" ", s)
    return PUNCT_RE.sub("", s)

def has_cjk(s):
    return bool(re.search(r"[一-鿿]", s or ""))

def char_ngrams(s, n=3):
    s = s or ""
    if not s:
        return set()
    if len(s) <= n:
        return {s}
    return {s[i:i + n] for i in range(len(s) - n + 1)}

def jaccard(a, b):
    a, b = set(a), set(b)
    if not a and not b:
        return 0.0
    u = a | b
    if not u:
        return 0.0
    return len(a & b) / len(u)

def title_similarity(t1, t2):
    """CJK 与 Latin 分别按字符 3-gram Jaccard；跨语言对不可比。"""
    n1, n2 = normalize_title(t1), normalize_title(t2)
    if not n1 or not n2:
        return 0.0, False
    c1, c2 = has_cjk(n1), has_cjk(n2)
    if c1 != c2:
        return 0.0, False
    return jaccard(char_ngrams(n1), char_ngrams(n2)), True

def venue_similarity(v1, v2):
    n1, n2 = normalize_venue(v1), normalize_venue(v2)
    if not n1 or not n2:
        return 0.0
    if has_cjk(n1) != has_cjk(n2):
        return 0.0
    return jaccard(char_ngrams(n1), char_ngrams(n2))

def surname(author):
    """粗取姓氏：'Smith, John'->Smith；'Wang, Li'->Wang；'张三'->张；'John Smith'->Smith。"""
    a = (author or "").strip()
    if not a:
        return ""
    if "," in a:
        return a.split(",", 1)[0].strip().lower()
    if has_cjk(a):
        return a[0]
    return a.split()[-1].lower()

def author_surnames(authors):
    return {surname(a) for a in (authors or []) if surname(a)}

def author_overlap(a1, a2):
    s1, s2 = author_surnames(a1), author_surnames(a2)
    return jaccard(s1, s2)

def norm_doi(d):
    d = (d or "").strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d.rstrip(".。")

FORMAL_TYPES = {"journal_article", "conference_paper", "book", "book_chapter",
                "thesis", "report", "standard", "patent"}
PREPRINT_TYPES = {"preprint", "misc"}

def type_compatibility(t1, t2):
    if t1 == t2:
        return "same"
    pair = {t1, t2}
    if pair <= (FORMAL_TYPES | PREPRINT_TYPES) and pair & PREPRINT_TYPES and pair & FORMAL_TYPES:
        return "preprint_formal"   # 期刊/会议 <-> 预印本：可合并（保留正式版）
    if "journal_article" in pair and "conference_paper" in pair:
        return "cautious"          # 期刊 <-> 会议：需谨慎（扩刊/会议版）
    return "difficult"

# ---------- 成对信号 ----------

def pair_signals(r1, r2):
    ts, comparable = title_similarity(r1.get("title"), r2.get("title"))
    d1, d2 = norm_doi(r1.get("doi")), norm_doi(r2.get("doi"))
    doi_match = bool(d1 and d2 and d1 == d2)
    y1, y2 = r1.get("year"), r2.get("year")
    year_diff = abs(int(y1) - int(y2)) if y1 and y2 else None
    ao = author_overlap(r1.get("authors"), r2.get("authors"))
    vs = venue_similarity(r1.get("venue"), r2.get("venue"))
    tc = type_compatibility(r1.get("entry_type", "misc"), r2.get("entry_type", "misc"))
    fa1 = surname((r1.get("authors") or [""])[0])
    fa2 = surname((r2.get("authors") or [""])[0])
    sig = {"title_sim": round(ts, 4), "comparable": comparable,
           "doi_match": doi_match, "year_diff": year_diff,
           "author_overlap": round(ao, 4), "venue_sim": round(vs, 4),
           "type_compatible": tc,
           "same_first_author": bool(fa1 and fa1 == fa2)}
    return sig

def classify_pair(r1, r2, sig):
    """返回 (tier, reasons[])。tier ∈ auto_merge|needs_review|protected|none"""
    reasons = []
    d1, d2 = norm_doi(r1.get("doi")), norm_doi(r2.get("doi"))
    # 禁止合并保护
    if d1 and d2 and d1 != d2:
        reasons.append(f"两个不同 DOI 均存在且不相同（{d1} vs {d2}），禁止合并")
        return "protected", reasons
    if (sig["same_first_author"] and sig["comparable"]
            and sig["year_diff"] == 0 and sig["title_sim"] < 0.60):
        reasons.append("同一第一作者、同一年、同语种但题名相似度<0.60，疑似同名作者的不同文献，禁止自动合并")
        return "protected", reasons
    # 自动合并
    if sig["doi_match"]:
        reasons.append("DOI 完全一致，自动合并")
        return "auto_merge", reasons
    if sig["title_sim"] >= 0.90 and sig["author_overlap"] >= 0.5 \
            and sig["year_diff"] is not None and sig["year_diff"] <= 1:
        reasons.append("title_sim>=0.90 且 author_overlap>=0.5 且 year_diff<=1，自动合并")
        return "auto_merge", reasons
    # 候选交 Agent
    potential = (sig["title_sim"] >= 0.50 or sig["author_overlap"] >= 0.5
                 or sig["doi_match"]
                 or (sig["same_first_author"] and sig["year_diff"] is not None
                     and sig["year_diff"] <= 1))
    cross_hint = (not sig["comparable"] and sig["author_overlap"] >= 0.5
                  and (sig["year_diff"] is None or sig["year_diff"] <= 1))
    if cross_hint:
        reasons.append("跨语言对但作者姓氏高度重合且年份接近：可能为同一文献的中/英文不同译名，交 Agent 裁决")
        return "needs_review", reasons
    if potential:
        if sig["title_sim"] >= 0.50:
            reasons.append("题名相似度中等，交 Agent 裁决")
        if sig["author_overlap"] >= 0.5:
            reasons.append("作者姓氏重合度>=0.5，交 Agent 裁决")
        if sig["same_first_author"] and sig["year_diff"] is not None and sig["year_diff"] <= 1:
            reasons.append("同一第一作者且年份接近，交 Agent 裁决")
        return "needs_review", reasons
    return "none", ["无合并潜质信号，不构成候选对"]

# ---------- candidates ----------

class DSU:
    def __init__(self, items):
        self.p = {x: x for x in items}
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra

def cmd_candidates(args):
    with open(args.library, encoding="utf-8") as f:
        lib = json.load(f)
    recs = lib.get("records", [])
    byid = {r["id"]: r for r in recs}
    pairs = []
    for a, b in itertools.combinations(recs, 2):
        sig = pair_signals(a, b)
        tier, reasons = classify_pair(a, b, sig)
        if tier == "none":
            continue
        pairs.append({"rid_a": a["id"], "rid_b": b["id"],
                      "title_a": a.get("title", ""), "title_b": b.get("title", ""),
                      "tier": tier, "signals": sig, "engine_reasons": reasons})
    # 组：auto_merge / needs_review 边做并查集；protected 对不并入组，
    # 且任何候选边不得把 protected 对的两个端点连进同一组（冲突边跳过并记录）。
    protected_ends = [(p["rid_a"], p["rid_b"]) for p in pairs if p["tier"] == "protected"]
    cand_edges = [p for p in pairs if p["tier"] in ("auto_merge", "needs_review")]
    def edge_strength(p):
        s = p["signals"]
        return (0 if p["tier"] == "auto_merge" else 1,
                -(s["title_sim"] + s["author_overlap"] + (1.0 if s["doi_match"] else 0.0)))
    cand_edges.sort(key=edge_strength)
    dsu = DSU([r["id"] for r in recs])
    members = {r["id"]: {r["id"]} for r in recs}
    skipped = []
    for p in cand_edges:
        ra, rb = dsu.find(p["rid_a"]), dsu.find(p["rid_b"])
        if ra == rb:
            continue
        conflict = any((pa in members[ra] and pb in members[rb])
                       or (pb in members[ra] and pa in members[rb])
                       for pa, pb in protected_ends)
        if conflict:
            skipped.append({"rid_a": p["rid_a"], "rid_b": p["rid_b"], "tier": p["tier"],
                            "reason": "该边会把禁止合并保护的记录对连入同一组，已跳过"})
            continue
        dsu.union(p["rid_a"], p["rid_b"])
        root = dsu.find(p["rid_a"])
        members.setdefault(root, set()).update(members[ra] | members[rb])
    groups = {}
    for p in cand_edges:
        g = dsu.find(p["rid_a"])
        if g not in members or p["rid_a"] not in members.get(g, set()):
            continue
        if any(s["rid_a"] == p["rid_a"] and s["rid_b"] == p["rid_b"] for s in skipped):
            continue
        groups.setdefault(g, {"group_id": None, "records": set(), "pairs": []})
        groups[g]["records"].update([p["rid_a"], p["rid_b"]])
        groups[g]["pairs"].append(p)
    out_groups = []
    for i, g in enumerate(sorted(groups.values(), key=lambda g: sorted(g["records"])), 1):
        g["group_id"] = f"G{i:03d}"
        tiers = {p["tier"] for p in g["pairs"]}
        g["tier"] = "auto_merge" if tiers == {"auto_merge"} else "needs_review"
        g["records"] = sorted(g["records"])
        g["pair_signals"] = {f"{p['rid_a']}~{p['rid_b']}": p["signals"] for p in g["pairs"]}
        g["engine_reasons"] = [f"[{p['rid_a']}~{p['rid_b']}] " + "；".join(p["engine_reasons"])
                               for p in g["pairs"]]
        out_groups.append(g)
    protected = [p for p in pairs if p["tier"] == "protected"]
    grouped = {rid for g in out_groups for rid in g["records"]}
    ungrouped = [r["id"] for r in recs if r["id"] not in grouped]
    out = {"count": len(recs), "n_pairs_scanned": len(recs) * (len(recs) - 1) // 2,
           "n_candidate_pairs": len(pairs), "groups": out_groups,
           "protected_pairs": protected, "skipped_edges": skipped,
           "ungrouped_records": ungrouped,
           "signal_definitions": {
               "title_sim": "归一化题名字符3-gram Jaccard(0-1)；跨语言对 comparable=false",
               "doi_match": "归一化 DOI 完全一致",
               "year_diff": "年份差绝对值",
               "author_overlap": "作者姓氏集合 Jaccard",
               "venue_sim": "刊会名归一化字符3-gram Jaccard",
               "type_compatible": "same|preprint_formal|cautious|difficult"}}
    os.makedirs(args.work, exist_ok=True)
    path = os.path.join(args.work, "merge_candidates.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[candidates] 扫描 {out['n_pairs_scanned']} 对，候选 {len(pairs)} 对，"
          f"组 {len(out_groups)} 个（自动合并 "
          f"{sum(1 for g in out_groups if g['tier']=='auto_merge')}），"
          f"保护对 {len(protected)}，未入组 {len(ungrouped)} 条 -> {path}")
    return 0

# ---------- apply ----------

CORE_FIELDS = ["title", "authors", "year", "entry_type", "venue", "volume",
               "issue", "pages", "doi", "language"]
PREFER_FORMAL = {"preprint_formal": 0, "same": 1, "cautious": 2, "difficult": 3}

def pick_keep(records):
    """组内择优保留：正式版 > 预印本；字段更全者优先。"""
    def score(r):
        fp = r.get("field_presence") or {}
        filled = sum(1 for k in ("title", "authors", "year", "venue", "volume",
                                 "issue", "pages", "doi") if fp.get(k) or r.get(k))
        formal_penalty = 0 if r.get("entry_type") in FORMAL_TYPES else 1
        return (formal_penalty, -filled, r["id"])
    return sorted(records, key=score)[0]

def reconcile_fields(keep, drops):
    """字段并集补全：keep 优先，缺失字段从 drops 补；冲突记入差异说明。"""
    merged = dict(keep)
    field_sources = {}
    diff_notes = []
    for k in CORE_FIELDS:
        vals = [(keep["id"], keep.get(k))] + [(d["id"], d.get(k)) for d in drops]
        vals = [(rid, v) for rid, v in vals if v not in (None, "", [])]
        if vals:
            field_sources[k] = vals[0][0]
            merged[k] = vals[0][1]
        else:
            field_sources[k] = None
            merged[k] = keep.get(k)
        if len(vals) > 1:
            distinct = []
            for rid, v in vals:
                if all(v != dv for _, dv in distinct):
                    distinct.append((rid, v))
            if len(distinct) > 1:
                keep_v = distinct[0][1]
                others = "；".join(f"{rid}={v}" for rid, v in distinct[1:])
                diff_notes.append(f"字段冲突[{k}]：以 keep({keep['id']})={keep_v} 为准；"
                                  f"被并条目取值：{others}")
    # extra_fields 并集 + arXiv 号保留
    extra = dict(keep.get("extra_fields") or {})
    for d in drops:
        for k, v in (d.get("extra_fields") or {}).items():
            if k not in extra and v not in (None, ""):
                extra[k] = v
        epr = (d.get("extra_fields") or {}).get("eprint") or d.get("eprint")
        if epr and "arxiv_id" not in extra:
            extra["arxiv_id"] = epr
            diff_notes.append(f"预印本 arXiv 号 {epr}（来自 {d['id']}）已保留进 extra_fields.arxiv_id")
    if keep.get("extra_fields") and "eprint" in keep.get("extra_fields", {}):
        extra.setdefault("arxiv_id", keep["extra_fields"]["eprint"])
    merged["extra_fields"] = extra
    # 合并来源溯源
    merged["merged_from"] = [keep["id"]] + [d["id"] for d in drops]
    fp = {k: bool(merged.get(k)) for k in ("title", "authors", "year", "venue",
                                           "volume", "issue", "pages", "doi")}
    fp["n_authors"] = len(merged.get("authors") or [])
    merged["field_presence"] = fp
    return merged, field_sources, diff_notes

def load_decisions(path):
    decisions = {}
    if not os.path.exists(path):
        return decisions, [f"裁决文件不存在: {path}"]
    errors = []
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception as e:
                errors.append(f"第 {ln} 行不是合法 JSON: {e}")
                continue
            gid = d.get("group_id")
            if not gid or d.get("action") not in ("merge", "keep_separate"):
                errors.append(f"第 {ln} 行缺少 group_id 或 action 非法: {line[:80]}")
                continue
            decisions[gid] = d
    return decisions, errors

def cmd_apply(args):
    with open(args.library, encoding="utf-8") as f:
        lib = json.load(f)
    recs = lib.get("records", [])
    byid = {r["id"]: r for r in recs}
    cand_path = os.path.join(args.work, "merge_candidates.json")
    groups = []
    protected_ends = []
    if os.path.exists(cand_path):
        with open(cand_path, encoding="utf-8") as f:
            cand = json.load(f)
            groups = cand.get("groups", [])
            protected_ends = [(p["rid_a"], p["rid_b"])
                              for p in cand.get("protected_pairs", [])]
    decisions, dec_errors = load_decisions(args.decisions)

    exceptions = list(dec_errors)
    applied, group_reports = [], []
    dropped_ids = set()
    for g in groups:
        gid = g["group_id"]
        d = decisions.get(gid)
        members = [byid[r] for r in g["records"] if r in byid]
        if d is None:
            exceptions.append(f"组 {gid} 未被裁决（Agent 必须逐组裁决），按 keep_separate 处理并记录")
            group_reports.append({"group_id": gid, "action": "keep_separate(undecided)",
                                  "records": g["records"],
                                  "signals": g.get("pair_signals", {}),
                                  "note": "缺裁决，保守保留分立"})
            continue
        if d["action"] == "keep_separate":
            group_reports.append({"group_id": gid, "action": "keep_separate",
                                  "records": g["records"],
                                  "signals": g.get("pair_signals", {}),
                                  "rationale": d.get("rationale", "")})
            continue
        # merge
        keep_rid = d.get("keep_rid")
        drop_rids = d.get("drop_rids") or []
        if keep_rid not in g["records"]:
            exceptions.append(f"组 {gid}: keep_rid {keep_rid} 不属于该组，改用引擎择优")
            keep_rid = None
        for r in drop_rids:
            if r not in g["records"]:
                exceptions.append(f"组 {gid}: drop_rid {r} 不属于该组，已忽略")
        drop_rids = [r for r in drop_rids if r in g["records"]]
        if keep_rid is None:
            keep = pick_keep(members)
            keep_rid = keep["id"]
        else:
            keep = byid[keep_rid]
        drops = [byid[r] for r in drop_rids if r != keep_rid and r in byid]
        merged_set = {keep_rid} | {d["id"] for d in drops}
        prot_hit = [(pa, pb) for pa, pb in protected_ends if pa in merged_set and pb in merged_set]
        if prot_hit:
            exceptions.append(f"组 {gid}: 裁决试图合并禁止合并保护对 {prot_hit}，已拒绝并 keep_separate")
            group_reports.append({"group_id": gid, "action": "keep_separate(protected)",
                                  "records": sorted(merged_set),
                                  "rationale": d.get("rationale", "")})
            continue
        if not drops:
            exceptions.append(f"组 {gid}: 裁决为 merge 但 drop_rids 为空，按 keep_separate 处理")
            group_reports.append({"group_id": gid, "action": "keep_separate(no drops)",
                                  "records": g["records"], "rationale": d.get("rationale", "")})
            continue
        merged, field_sources, diff_notes = reconcile_fields(keep, drops)
        applied.append((gid, g, merged, field_sources, diff_notes, d))
        dropped_ids.update(d["id"] for d in drops)

    kept_records = [r for r in recs if r["id"] not in dropped_ids]
    for gid, g, merged, fs, dn, d in applied:
        for i, r in enumerate(kept_records):
            if r["id"] == merged["merged_from"][0]:
                kept_records[i] = merged
                break
    os.makedirs(args.out, exist_ok=True)
    dedup_lib = {"records": kept_records, "count": len(kept_records),
                 "source_count": len(recs), "dropped": sorted(dropped_ids),
                 "merged_groups": [a[0] for a in applied]}
    with open(os.path.join(args.out, "library_deduped.json"), "w", encoding="utf-8") as f:
        json.dump(dedup_lib, f, ensure_ascii=False, indent=2)

    # 合并报告（人读 md + 机读 json）
    lines = ["# 文献去重与条目归并报告", "",
             f"- 原始条目: {len(recs)}；合并后条目: {len(kept_records)}；"
             f"合并组数: {len(applied)}；分立组数: "
             f"{sum(1 for r in group_reports if 'keep_separate' in r['action'])}", ""]
    rep_json = {"source_count": len(recs), "deduped_count": len(kept_records),
                "merged": [], "kept_separate": [], "exceptions": exceptions}
    for gid, g, merged, fs, dn, d in applied:
        lines.append(f"## 组 {gid}：合并 → 保留 {merged['merged_from'][0]}，"
                     f"并入 {'、'.join(merged['merged_from'][1:])}")
        lines.append("")
        lines.append(f"**Agent 裁决理由**：{d.get('rationale', '')}")
        lines.append("")
        lines.append("### 判据信号表")
        lines.append("")
        lines.append("| 记录对 | title_sim | doi_match | year_diff | author_overlap | venue_sim | type_compatible |")
        lines.append("|---|---|---|---|---|---|---|")
        for pairkey, sig in g.get("pair_signals", {}).items():
            lines.append(f"| {pairkey} | {sig['title_sim']}"
                         f"{'（跨语言不可比）' if not sig['comparable'] else ''} | "
                         f"{sig['doi_match']} | {sig['year_diff']} | "
                         f"{sig['author_overlap']} | {sig['venue_sim']} | "
                         f"{sig['type_compatible']} |")
        lines.append("")
        lines.append("### 保留字段来源")
        lines.append("")
        for k in CORE_FIELDS:
            lines.append(f"- {k}: {fs.get(k)}")
        lines.append("")
        lines.append("### 差异说明")
        lines.append("")
        lines.extend([f"- {x}" for x in dn] or ["- 无字段冲突；缺失字段已由并集补全"])
        lines.append("")
        rep_json["merged"].append({"group_id": gid, "kept": merged["merged_from"][0],
                                   "dropped": merged["merged_from"][1:],
                                   "signals": g.get("pair_signals", {}),
                                   "field_sources": fs, "diff_notes": dn,
                                   "rationale": d.get("rationale", "")})
    for r in group_reports:
        if "keep_separate" in r["action"]:
            rep_json["kept_separate"].append(r)
            lines.append(f"## 组 {r['group_id']}：保持分立（{r['action']}）")
            lines.append("")
            lines.append(f"- 记录: {'、'.join(r['records'])}")
            if r.get("rationale"):
                lines.append(f"- 理由：{r['rationale']}")
            lines.append("")
    if exceptions:
        lines.append("## 异常与保守处置")
        lines.append("")
        lines.extend([f"- {e}" for e in exceptions])
        lines.append("")
    with open(os.path.join(args.out, "merge_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    os.makedirs(args.work, exist_ok=True)
    with open(os.path.join(args.work, "merge_report.json"), "w", encoding="utf-8") as f:
        json.dump(rep_json, f, ensure_ascii=False, indent=2)

    # 编号映射（稿件参考文献表 -> 条目可匹配时）
    mapping_written = False
    if args.manuscript and os.path.exists(args.manuscript):
        try:
            with open(args.manuscript, encoding="utf-8") as f:
                ms = json.load(f)
            ref_paras = [p for p in ms.get("paragraphs", [])
                         if p.get("kind") == "reference_list"]
            num2rid = {}
            rid2num = {}
            for p in ref_paras:
                m = re.match(r"^\[(\d+)\]\s*(.+)$", p.get("text", "").strip())
                if not m:
                    continue
                num, text = int(m.group(1)), m.group(2)
                best, best_sim = None, 0.0
                for r in recs:
                    nt = normalize_title(r.get("title"))
                    if nt and (nt in PUNCT_RE.sub("", normalize_title(text))
                               or PUNCT_RE.sub("", normalize_title(text)).find(nt) >= 0):
                        best, best_sim = r["id"], 1.0
                        break
                if best:
                    num2rid[num] = best
                    rid2num[best] = num
            kept_ids = [r["id"] for r in kept_records]
            dedup_mapping = {"rid_mapping": {}, "number_mapping": {},
                             "new_order_rids": kept_ids, "limits": []}
            for gid, g, merged, fs, dn, d in applied:
                keep_rid = merged["merged_from"][0]
                for dr in merged["merged_from"][1:]:
                    dedup_mapping["rid_mapping"][dr] = keep_rid
                    if dr in rid2num and keep_rid in rid2num:
                        dedup_mapping["number_mapping"][str(rid2num[dr])] = rid2num[keep_rid]
                    elif dr in rid2num:
                        dedup_mapping["limits"].append(
                            f"编号 {rid2num[dr]}（{dr}）的 keep 条目 {keep_rid} 未在稿件参考文献表中匹配到编号，"
                            f"无法给出编号映射，仅给出 rid 映射")
            if not ref_paras:
                dedup_mapping["limits"].append("稿件无 reference_list 段落，仅给出 rid 映射")
            elif not num2rid:
                dedup_mapping["limits"].append("稿件参考文献表条目与文献库记录未能按题名匹配，仅给出 rid 映射")
            mp = os.path.join(args.work, "dedup_mapping.json")
            with open(mp, "w", encoding="utf-8") as f:
                json.dump(dedup_mapping, f, ensure_ascii=False, indent=2)
            mapping_written = True
        except Exception as e:
            exceptions.append(f"dedup_mapping 生成失败: {e}")
    print(f"[apply] {len(recs)} -> {len(kept_records)} 条；合并 {len(applied)} 组；"
          f"分立 {len(rep_json['kept_separate'])} 组；异常 {len(exceptions)}；"
          f"编号映射 {'已写' if mapping_written else '未生成（无稿件或不匹配）'}")
    return 0

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("candidates")
    p.add_argument("--library", required=True)
    p.add_argument("--work", default="/app/work")
    p.set_defaults(fn=cmd_candidates)
    p = sub.add_parser("apply")
    p.add_argument("--library", required=True)
    p.add_argument("--decisions", required=True)
    p.add_argument("--work", default="/app/work")
    p.add_argument("--out", default="/app/output")
    p.add_argument("--manuscript")
    p.set_defaults(fn=cmd_apply)
    args = ap.parse_args()
    return args.fn(args)

if __name__ == "__main__":
    sys.exit(main())
