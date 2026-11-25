#!/usr/bin/env python3
"""build_deliverables.py — 共享交付引擎：论断-引用绑定落地 + 锚点核验 + 四要素完整性 + 参考文献渲染。

用法: python3 build_deliverables.py --work /app/work --out /app/output
输入（work/ 下）:
  draft_intro.md      引言工作稿（含 〔E#〕 证据锚点，不得手写 [n] 编号）
  draft_rl.md         相关工作工作稿（同上）
  evidence_map.json   [{eid, type, source:{kind, loc}, quote, note?}]
  claim_bindings.jsonl 每行 {loc: intro|rl, sentence, entry_ids[], eids[], claim_type}
  library.json        parse_library.py 产物（entry 元数据）
输出（/app/output）:
  introduction.md / related_work.md / references.md / evidence_map.json / build_report.json
规则:
  1) 每个 〔E#〕 必须能在 evidence_map.json 中找到；否则记 exceptions 并保留原文（由 Agent 修复）。
  2) 每条 binding 的 sentence 必须在对应工作稿中逐字（空白归一化后）找到；entry_ids 必须存在于 library。
  3) 引用编号由本引擎按首次出现顺序（先引言后相关工作）统一分配；同句多引合并为 [n,m]；
     注入位置为句末标点之前。Agent 手写的数字引用会被检出并告警（agent_pre_numbered）。
  4) 四要素完整性：引言须含 背景/问题、空白、贡献 三组标题信号；相关工作须含 ≥1 个分组小节。
"""
import argparse, json, os, re, sys, unicodedata

ANCHOR_RE = re.compile(r"〔(E\d+)〕")
NUM_CITE_RE = re.compile(r"\[(\d+(?:\s*[-–,，]\s*\d+)*)\]")
PUNCT_TAIL = "。；！？;!?\"')）】」』"
PUNCT_ALL = set("。；;，,、：:．.！!？?\"'“”‘’（）()《》〈〉【】〖〗〔〕")

TYPE_MARK = {"journal_article": "[J]", "conference_paper": "[C]", "book": "[M]",
             "book_chapter": "[M]", "thesis": "[D]", "patent": "[P]", "standard": "[S]",
             "report": "[R]", "preprint": "[EB/OL]", "misc": "[Z]"}

def norm(s):
    return re.sub(r"\s+", " ", s).strip()

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def load_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                rows.append({"_error": f"第{i}行解析失败: {e}"})
    return rows

def find_sentence_span(text, sentence):
    """在原始 text 中定位 sentence（空白/标点容忍），返回 (start, end)（原始坐标）。
    两级策略：
      1) 空白容忍正则：sentence 归一化后逐字匹配（空格匹配任意空白）；
      2) fuzzy：去除全部标点后匹配，并将坐标映射回原文。
    找不到返回 None。"""
    s = norm(ANCHOR_RE.sub("", sentence))
    if not s:
        return None
    pat = re.compile(re.escape(s).replace("\\ ", "\\s+"))
    m = pat.search(text)
    if m:
        return (m.start(), m.end())
    s2 = "".join(ch for ch in s if ch not in PUNCT_ALL)
    if not s2:
        return None
    raw_map = []
    chars = []
    for i, ch in enumerate(text):
        if ch not in PUNCT_ALL:
            raw_map.append(i)
            chars.append(ch)
    t2 = "".join(chars)
    idx2 = t2.find(s2)
    if idx2 < 0:
        return None
    raw_start = raw_map[idx2]
    raw_end = raw_map[idx2 + len(s2) - 1] + 1
    return (raw_start, raw_end)

def inject_citation(text, span, nums):
    """在 span 结尾（句末标点之前）注入 [n]。"""
    start, end = span
    tail = end
    while tail > start and text[tail - 1] in PUNCT_TAIL:
        tail -= 1
    label = "[" + ",".join(str(n) for n in nums) + "]"
    return text[:tail] + label + text[tail:]

def fmt_authors(authors, cjk):
    if not authors:
        return ""
    if len(authors) <= 3:
        return ", ".join(authors)
    head = ", ".join(authors[:3])
    return head + ("，等" if cjk else ", et al")

def render_reference(n, rec):
    title = (rec.get("title") or "").strip().rstrip(".。")
    if not title:
        title = "（题名字段缺失）"
    cjk = bool(re.search(r"[\u4e00-\u9fff]", title))
    authors = fmt_authors(rec.get("authors") or [], cjk)
    mark = TYPE_MARK.get(rec.get("entry_type"), "[Z]")
    venue = (rec.get("venue") or "").strip()
    year = rec.get("year") or ""
    vol = rec.get("volume") or ""
    issue = rec.get("issue") or ""
    pages = rec.get("pages") or ""
    tail = []
    if venue:
        tail.append(venue)
    yv = ""
    if year:
        yv = str(year)
        if vol:
            yv += f", {vol}"
            if issue:
                yv += f"({issue})"
        if pages:
            yv += f": {pages}"
    if yv:
        tail.append(yv)
    src = ", ".join(tail)
    mid = f". {src}" if src else ""
    auth = f"{authors}. " if authors else ""
    return f"[{n}] {auth}{title}{mark}{mid}."

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    report = {"anchors": {"total": 0, "resolved": 0, "missing": []},
              "bindings": {"total": 0, "matched": 0, "missed": [], "orphan_entries": []},
              "agent_pre_numbered": [],
              "sections": {"intro_background": False, "intro_gap": False,
                           "intro_contributions": False, "rl_groups": 0},
              "length": {}, "reference_order": [], "reference_style": "GB/T 7714 numeric",
              "issues": []}
    exceptions = []

    ev = load_json(os.path.join(args.work, "evidence_map.json"), []) or []
    eids = {e.get("eid") for e in ev if isinstance(e, dict)}
    lib = load_json(os.path.join(args.work, "library.json"), {}) or {}
    records = {r.get("id"): r for r in lib.get("records", []) if r.get("id")}

    drafts_raw = {}
    for key, fname in (("intro", "draft_intro.md"), ("rl", "draft_rl.md")):
        p = os.path.join(args.work, fname)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                drafts_raw[key] = f.read()
        else:
            drafts_raw[key] = None
            exceptions.append({"type": "missing_draft", "file": fname,
                               "handling": "关键产物缺失，交付将降级为 partial"})

    # ---- 锚点核验（在去锚点前的原文上统计）----
    for key in ("intro", "rl"):
        if not drafts_raw[key]:
            continue
        for m in ANCHOR_RE.finditer(drafts_raw[key]):
            report["anchors"]["total"] += 1
            if m.group(1) in eids:
                report["anchors"]["resolved"] += 1
            else:
                report["anchors"]["missing"].append({"loc": key, "eid": m.group(1)})

    # 后续所有匹配均在去锚点文本上进行（绑定句与草稿保持一致）
    drafts = {k: (ANCHOR_RE.sub("", v) if v else None) for k, v in drafts_raw.items()}

    # ---- 绑定核验与编号分配 ----
    bindings = [b for b in load_jsonl(os.path.join(args.work, "claim_bindings.jsonl"))
                if isinstance(b, dict) and not b.get("_error")]
    for b in load_jsonl(os.path.join(args.work, "claim_bindings.jsonl")):
        if isinstance(b, dict) and b.get("_error"):
            exceptions.append({"type": "binding_parse", "detail": b["_error"]})

    merged = {}  # (loc, sentence_norm) -> {entry_ids:set, eids:set, claim_type}
    order_seq = []
    for b in bindings:
        report["bindings"]["total"] += 1
        loc = b.get("loc") if b.get("loc") in ("intro", "rl") else "rl"
        sentence = b.get("sentence") or ""
        if not drafts.get(loc):
            report["bindings"]["missed"].append({"loc": loc, "sentence": sentence[:60],
                                                 "reason": "draft_missing"})
            continue
        span = find_sentence_span(drafts[loc], sentence)
        if span is None:
            report["bindings"]["missed"].append({"loc": loc, "sentence": sentence[:60],
                                                 "reason": "sentence_not_found"})
            continue
        for eid in (b.get("eids") or []):
            if eid not in eids:
                exceptions.append({"type": "binding_eid_unknown", "eid": eid,
                                   "sentence": sentence[:60]})
        bad_entries = [e for e in (b.get("entry_ids") or []) if e not in records]
        for e in bad_entries:
            exceptions.append({"type": "binding_entry_unknown", "entry_id": e,
                               "sentence": sentence[:60],
                               "handling": "该文献未纳入编号与文献表"})
        key = (loc, norm(sentence))
        if key not in merged:
            merged[key] = {"entry_ids": [], "seen": set(), "eids": [],
                           "claim_type": b.get("claim_type")}
            order_seq.append(key)
        for e in (b.get("entry_ids") or []):
            if e in records and e not in merged[key]["seen"]:
                merged[key]["seen"].add(e)
                merged[key]["entry_ids"].append(e)
        for eid in (b.get("eids") or []):
            if eid in eids and eid not in merged[key]["eids"]:
                merged[key]["eids"].append(eid)
        report["bindings"]["matched"] += 1

    # 编号：按首次出现顺序
    num_of = {}
    for key in order_seq:
        for e in merged[key]["entry_ids"]:
            if e not in num_of:
                num_of[e] = len(num_of) + 1
    report["reference_order"] = [f"{n}={e}" for e, n in
                                 sorted(num_of.items(), key=lambda kv: kv[1])]

    # 检出 Agent 手写编号
    for key in ("intro", "rl"):
        if not drafts[key]:
            continue
        for m in NUM_CITE_RE.finditer(drafts[key]):
            report["agent_pre_numbered"].append({"loc": key, "raw": m.group(0)})

    # ---- 注入引用并清稿 ----
    clean = {}
    for key in ("intro", "rl"):
        if not drafts[key]:
            clean[key] = None
            continue
        text = drafts[key]
        # 先清除锚点标记，再注入引用编号（避免注入位置落入锚点内部）
        text = ANCHOR_RE.sub("", text)
        # 从后往前注入，避免偏移失效
        injects = []
        for (loc, s_norm), info in merged.items():
            if loc != key or not info["entry_ids"]:
                continue
            span = find_sentence_span(text, s_norm)
            if not span:
                continue
            nums = sorted(num_of[e] for e in info["entry_ids"])
            injects.append((span[1], nums))
        for pos, nums in sorted(injects, reverse=True):
            tail = pos
            while tail > 0 and text[tail - 1] in PUNCT_TAIL:
                tail -= 1
            label = "[" + ",".join(str(n) for n in nums) + "]"
            text = text[:tail] + label + text[tail:]
        text = ANCHOR_RE.sub("", text)
        text = re.sub(r"[ \t]+", " ", text)
        clean[key] = text.strip()

    # ---- 四要素完整性 ----
    if clean.get("intro"):
        t = clean["intro"]
        report["sections"]["intro_background"] = bool(re.search(r"背景|问题|现状", t))
        report["sections"]["intro_gap"] = bool(re.search(r"空白|不足|挑战|局限|缺口|尚未|有待", t))
        report["sections"]["intro_contributions"] = bool(re.search(r"贡献|本文的?工作|本工作的?主要", t))
        report["length"]["intro_chars"] = len(re.sub(r"\s", "", t))
    if clean.get("rl"):
        t = clean["rl"]
        report["sections"]["rl_groups"] = len(re.findall(r"^#{2,3}\s", t, re.M))
        report["length"]["rl_chars"] = len(re.sub(r"\s", "", t))
    if report["length"].get("intro_chars", 0) < 250:
        report["issues"].append("intro_too_short(<250字)")
    if report["length"].get("rl_chars", 0) < 350:
        report["issues"].append("rl_too_short(<350字)")

    # ---- 参考文献表 ----
    refs_md = ["# 参考文献", ""]
    used_entries = [e for e, _ in sorted(num_of.items(), key=lambda kv: kv[1])]
    for i, e in enumerate(used_entries, 1):
        refs_md.append(render_reference(i, records.get(e, {})))
        refs_md.append("")
    if not used_entries:
        refs_md.append("（本案例未产生任何文献引用——请检查 claim_bindings.jsonl 与材料）")
        exceptions.append({"type": "no_references_cited",
                           "handling": "引用为零：相关工作写作未绑定任何文献，交付降级"})

    # ---- v2.0.2：论断-引用审计表（引擎自证，供评审逐条复核）----
    ev_by_id = {e.get("eid"): e for e in ev if isinstance(e, dict)}
    audit = ["# 论断-引用审计表", "",
             "由 build_deliverables.py 自动生成：每条已注入引用的论断句 → 引用编号 → 文献元数据 → 证据锚点。",
             "",
             "| # | 位置 | 论断句（截断） | 类型 | 引用 | 文献（编号=条目: 题名(来源, 年)） | 证据锚点 |",
             "|---|---|---|---|---|---|---|"]
    for i, (loc, s_norm) in enumerate(order_seq, 1):
        info = merged.get((loc, s_norm))
        if not info or not info["entry_ids"]:
            continue
        nums = sorted(num_of[e] for e in info["entry_ids"])
        entries_txt = "; ".join(
            f"[{num_of[e]}]={e}: {(records.get(e, {}).get('title') or '')[:36]}"
            f"({records.get(e, {}).get('venue', '')}, {records.get(e, {}).get('year', '?')})"
            for e in info["entry_ids"]).replace("|", "/")
        eid_txt = ", ".join(info["eids"]) or "—"
        quote_txt = ""
        if info["eids"]:
            q = (ev_by_id.get(info["eids"][0], {}) or {}).get("quote", "")
            if q:
                quote_txt = f"；首条证据摘录: {q[:40]}"
        sent = re.sub(r"〔E\d+〕", "", s_norm)[:60].replace("|", "/")
        audit.append(f"| {i} | {'引言' if loc == 'intro' else '相关工作'} | {sent} | "
                     f"{info.get('claim_type') or '—'} | [{','.join(map(str, nums))}] | "
                     f"{entries_txt} | {eid_txt}{quote_txt} |")
    audit.append("")
    audit.append(f"共 {sum(1 for k in order_seq if merged.get(k, {}).get('entry_ids'))} 条注入引用；"
                 f"编号按首次出现顺序由引擎分配。")
    audit_txt = "\n".join(audit)

    # ---- 落盘 ----
    def w(name, content):
        if content is None:
            return
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
            f.write(content)

    w("introduction.md", clean.get("intro"))
    w("citation_audit_table.md", audit_txt)
    w("related_work.md", clean.get("rl"))
    w("references.md", "\n".join(refs_md))
    with open(os.path.join(args.out, "evidence_map.json"), "w", encoding="utf-8") as f:
        json.dump(ev, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "build_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # exceptions 合并回 work/exceptions.json（供 assemble_result 汇总）
    ex_path = os.path.join(args.work, "exceptions.json")
    old = load_json(ex_path, []) or []
    old.extend(exceptions)
    with open(ex_path, "w", encoding="utf-8") as f:
        json.dump(old, f, ensure_ascii=False, indent=2)

    print(f"[build] 锚点 {report['anchors']['resolved']}/{report['anchors']['total']} "
          f"绑定 {report['bindings']['matched']}/{report['bindings']['total']} "
          f"文献 {len(used_entries)} 条 "
          f"四要素 背景={report['sections']['intro_background']} 空白={report['sections']['intro_gap']} "
          f"贡献={report['sections']['intro_contributions']} 分组={report['sections']['rl_groups']}")
    for iss in report["issues"]:
        print(f"[build][issue] {iss}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
