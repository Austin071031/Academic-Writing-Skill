#!/usr/bin/env python3
"""outline_engine.py — 章节规划与篇幅论证对齐引擎（方向：立得住）。

子命令：
  plan    解析大纲 → outline.json；材料-大纲覆盖映射 → chapter_plan.json /
          chapter_plan.md / coverage_report.md；检测章节重复与材料缺口。
  check   校验新写章节：编号连续性、必备论证要素、篇幅偏差、
          数字可溯源性（逐值对照材料，容差仅豁免舍入）→ chapter_check.json。

用法:
  python3 outline_engine.py plan --chapters work/chapters.json --outline <大纲文件>
      [--materials work/materials.json] [--work /app/work]
  python3 outline_engine.py check --chapter <新章节.md> --chapters work/chapters.json
      --plan work/chapter_plan.json [--materials work/materials.json] [--work /app/work]

判据（references/planning_rules.md 与之一致，Agent 不得另行发明）:
  - 覆盖得分：标题+要素短语与章节文本的字符 2-gram Jaccard ≥ 0.06 视为相关。
  - 篇幅偏差：实际字数 / 大纲预算 - 1，|偏差| > 25% 记 WARN，> 50% 记 ISSUE。
  - 必备要素：研究问题、方法、结果、讨论、局限（同义词表见 planning_rules.md）。
  - 数字溯源：章节中每个数值必须 (a) 原样出现于材料，或 (b) 可由材料两个值
    经四则运算在 ±1% 内复现（如提升百分比），否则进 unverified 列表（不臆造、只标记）。
"""
import argparse, json, math, os, re, sys

REQUIRED_ELEMENTS = {
    "研究问题": ["研究问题", "研究目标", "科学问题", "旨在", "本文提出", "本文旨在"],
    "方法": ["方法", "实验", "制备", "测量", "表征", "流程"],
    "结果": ["结果", "表明", "显示", "测得", "达到", "获得"],
    "讨论": ["讨论", "归因", "机制", "解释", "相比", "原因"],
    "局限": ["局限", "不足", "展望", "限制", "尚未", "仍需"],
}
BUDGET_RE = re.compile(r"[（(]约\s*(\d+(?:\.\d+)?)\s*字[)）]")
NUM_TOKEN = re.compile(r"(?<![\w./-])-?\d+(?:\.\d+)?")
NUM_WITH_UNIT = re.compile(r"(?<![\w./-])(-?\d+(?:\.\d+)?)\s*(mS/cm|S/cm|°C|h|min|%|nm|μm|um|GPa|MPa|mAh/g|V|kHz|MHz|GHz|Ω|ohm)")
XREF_MASK = re.compile(r"(图|表|式|公式|Fig\.?|Table\.?|Eq\.?)\s*\d+(?:[-–.]\d+)?")
HEADING_NUM_LINE = re.compile(r"^(#{1,6}\s*)\d+(?:\.\d+)+")

def mask_nonfacts(text):
    """遮蔽图表/公式交叉引用与章节标题编号，避免误当事实数值。"""
    lines = []
    for ln in text.splitlines():
        m = HEADING_NUM_LINE.match(ln)
        if m:
            ln = m.group(1) + " " * 8 + ln[m.end():]
        lines.append(ln)
    return XREF_MASK.sub(" ", "\n".join(lines))

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def ngrams(text, n=2):
    text = re.sub(r"\s+", "", text)
    return {text[i:i + n] for i in range(max(0, len(text) - n + 1))} or {text}

def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)

def parse_outline(path):
    """大纲 → [{oid, level, number, title, budget_chars, elements[], source_line}]"""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception as e:
        print(f"[outline_engine] 大纲读取失败: {e}", file=sys.stderr)
        return []
    entries, seq = [], 0
    for ln in lines:
        t = ln.strip()
        if not t:
            continue
        m = re.match(r"^(#{1,6})\s+(.+)$", t)
        if m:
            level, body = len(m.group(1)), m.group(2).strip()
        else:
            m2 = re.match(r"^(\d+(?:\.\d+){0,3})\s*[\.、]?\s*(\S.*)$", t)
            m3 = re.match(r"^第([一二三四五六七八九十\d]+)章\s*(\S.*)$", t)
            if m3:
                level, body = 1, t
            elif m2:
                level, body = m2.group(1).count(".") + 1, t
            elif entries and re.search(r"[；;，,、]", t):
                # 标题下方的要素描述行 → 归入上一条目
                parts = [x.strip() for x in re.split(r"[；;，,]", t) if x.strip()]
                for x in parts:
                    if x not in entries[-1]["elements"] and x != entries[-1]["title"]:
                        entries[-1]["elements"].append(x)
                continue
            else:
                continue
        seq += 1
        budget = None
        bm = BUDGET_RE.search(body)
        if bm:
            budget = int(float(bm.group(1)))
            body = BUDGET_RE.sub("", body).strip()
        num = None
        nm = re.match(r"^(\d+(?:\.\d+){0,3})[\s\.、](\S.*)$", body)
        if nm:
            num, body = nm.group(1), nm.group(2).strip()
        else:
            cm = re.match(r"^第([一二三四五六七八九十\d]+)章\s*(\S.*)$", body)
            if cm:
                num, body = cm.group(1), cm.group(2).strip()
        rest = body
        title = re.split(r"[：:，,；;]", rest)[0].strip()
        elements = [e.strip() for e in re.split(r"[；;]", rest)
                    for e in e.split("，") if e.strip() and e.strip() != title]
        entries.append({"oid": f"O{seq:02d}", "level": level, "number": num,
                        "title": title, "budget_chars": budget,
                        "elements": elements, "source_line": ln.strip()})
    # 跳过文档总标题（如「论文大纲」「提纲」本身）
    entries = [e for e in entries if e["title"] not in
               ("论文大纲", "大纲", "提纲", "论文提纲", "目录", "outline")]
    for i, e in enumerate(entries, 1):
        e["oid"] = f"O{i:02d}"
    return entries

def coverage_map(entries, chapters):
    """每个大纲条目 ← 已有章节段落；返回 (mapping, gaps, section_scores)"""
    paras = chapters.get("paragraphs", [])
    sec_of = {}
    for s in chapters.get("sections", []):
        for p in s["paragraphs"]:
            sec_of[p["pid"]] = s
    mapping, gaps = [], []
    sec_hits = {s["sid"]: set() for s in chapters.get("sections", [])}
    for e in entries:
        key = ngrams(e["title"] + " ".join(e["elements"]))
        hits, seen = [], set()
        # 1) 直接映射：章节号一致或标题包含
        for s in chapters.get("sections", []):
            sn, st = s.get("heading_number"), s.get("title", "")
            direct = (e["number"] and sn and str(e["number"]) == str(sn)) or \
                     (len(e["title"]) >= 2 and e["title"] in st)
            if direct:
                for p in s["paragraphs"]:
                    if p["kind"] == "reference_list":
                        continue
                    hits.append({"pid": p["pid"], "sid": s["sid"], "score": 1.0,
                                 "section_title": st, "match": "direct_section",
                                 "excerpt": p["text"][:80]})
                    seen.add(p["pid"])
                    sec_hits[s["sid"]].add(e["oid"])
        # 2) 关键词补充命中
        for p in paras:
            if p["kind"] in ("reference_list",) or p["pid"] in seen:
                continue
            score = jaccard(key, ngrams(p["text"]))
            if score >= 0.06:
                hits.append({"pid": p["pid"], "sid": sec_of[p["pid"]]["sid"],
                             "score": round(score, 3), "match": "keyword",
                             "section_title": sec_of[p["pid"]]["title"],
                             "excerpt": p["text"][:80]})
                sec_hits[sec_of[p["pid"]]["sid"]].add(e["oid"])
        hits.sort(key=lambda h: -h["score"])
        mapping.append({"oid": e["oid"], "title": e["title"],
                        "budget_chars": e["budget_chars"],
                        "elements": e["elements"],
                        "evidence_pids": [h["pid"] for h in hits[:8]],
                        "coverage": hits[:8],
                        "n_hits": len(hits)})
    for p in paras:
        if p["kind"] == "reference_list":
            continue
        sid = sec_of[p["pid"]]["sid"]
        if not sec_hits.get(sid) and len(p["text"]) > 40:
            gaps.append({"pid": p["pid"], "sid": sid,
                         "excerpt": p["text"][:100]})
    return mapping, gaps, sec_hits

def redundancy(entries, mapping):
    """章节对材料重叠（同一章材料被两个以上大纲条目强覆盖 → 重复风险）"""
    pairs = []
    cov = {e["oid"]: set(h["pid"] for h in m["coverage"])
           for e, m in zip(entries, mapping)}
    els = list(entries)
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            a, b = cov[els[i]["oid"]], cov[els[j]["oid"]]
            if not a or not b:
                continue
            ov = len(a & b) / min(len(a), len(b))
            if ov >= 0.5:
                pairs.append({"oids": [els[i]["oid"], els[j]["oid"]],
                              "titles": [els[i]["title"], els[j]["title"]],
                              "overlap_ratio": round(ov, 2)})
    return pairs

def required_elements(entries):
    """提纲级必备要素完整性（研究问题/方法/结果/讨论/局限是否都有章节承接）"""
    text_all = " ".join(e["title"] + " ".join(e["elements"]) for e in entries)
    return {k: any(w in text_all for w in words)
            for k, words in REQUIRED_ELEMENTS.items()}

def extract_numbers(text):
    """带单位数值优先；无单位数字单独登记（排除编号类上下文）"""
    out = []
    for m in NUM_WITH_UNIT.finditer(text):
        out.append({"raw": m.group(0), "value": float(m.group(1)),
                    "unit": m.group(2), "kind": "unit"})
    for m in NUM_TOKEN.finditer(text):
        s = m.group(0)
        try:
            v = float(s)
        except ValueError:
            continue
        if abs(v) >= 1000 and v == int(v) and 1900 <= v <= 2100:
            continue  # 年份豁免
        out.append({"raw": s, "value": v, "unit": None, "kind": "plain"})
    return out

def numbers_traceable(chapter_text, materials_text):
    """逐值溯源：(a) 原文出现（含单位差异写法）；(b) 两值四则复现（±1%，含百分比换算）"""
    mats = extract_numbers(mask_nonfacts(materials_text))
    mat_vals = [m["value"] for m in mats]
    results = []
    for num in extract_numbers(mask_nonfacts(chapter_text)):
        v = num["value"]
        if v in mat_vals or f"{v:g}" in re.sub(r"\s+", "", materials_text):
            results.append({**num, "status": "verbatim"})
            continue
        cands = [v]
        if num["unit"] == "%" or abs(v) > 1:
            cands.append(v / 100.0)
        derived = False
        for a in mat_vals:
            for b in mat_vals:
                if b == 0:
                    continue
                for expr, val in ((f"{a}/{b}", a / b), (f"{a}-{b}", a - b),
                                  (f"({a}-{b})/{b}", (a - b) / b), (f"{a}+{b}", a + b)):
                    for target in cands:
                        if val != 0 and abs(val - target) / abs(val) <= 0.01:
                            results.append({**num, "status": "derived",
                                            "derivation": f"{expr}={val:.4g}≈{target:g}"})
                            derived = True
                            break
                    if derived:
                        break
                if derived:
                    break
            if derived:
                break
        if not derived:
            results.append({**num, "status": "unverified"})
    return results

def cmd_plan(args):
    chapters = load_json(args.chapters, {}) or {}
    entries = parse_outline(args.outline)
    if not entries:
        print("[outline_engine] 大纲无条目，outline.json 为空", file=sys.stderr)
    mapping, gaps, _ = coverage_map(entries, chapters)
    pairs = redundancy(entries, mapping)
    elements_ok = required_elements(entries)
    total_budget = sum(e["budget_chars"] or 0 for e in entries)
    actual = chapters.get("total_chars", 0)
    outline = {"outline_file": args.outline, "entries": entries,
               "total_budget_chars": total_budget, "actual_chars": actual,
               "required_elements": elements_ok}
    plan = {"outline": args.outline, "generated_from": {
                "chapters": args.chapters,
                "n_material_paragraphs": chapters.get("n_paragraphs", 0)},
            "sections": [], "redundancy_pairs": pairs, "material_gaps": gaps[:50]}
    for e, m in zip(entries, mapping):
        sec = {"oid": e["oid"], "title": e["title"], "level": e["level"],
               "number": e["number"],
               "budget_chars": e["budget_chars"],
               "actual_chars": sum(h.get("_chars", 0) for h in []),
               "question": f"本节需要回答：{e['title']}（{'; '.join(e['elements']) or '要素未声明'}）",
               "required_elements": e["elements"],
               "evidence_pids": m["evidence_pids"],
               "coverage": m["coverage"],
               "coverage_status": "covered" if m["n_hits"] else
                                  ("partial" if e["level"] > 1 else "no_material_yet"),
               "word_budget_ratio": (round(e["budget_chars"] / total_budget, 3)
                                     if e["budget_chars"] and total_budget else None)}
        plan["sections"].append(sec)
    # chapter_plan.md
    lines = ["# 章节规划（chapter plan）", "",
             f"来源：大纲 `{os.path.basename(args.outline)}`；材料：{chapters.get('n_paragraphs', 0)} 段，共 {actual} 字。",
             ""]
    for sec in plan["sections"]:
        bud = f"预算约 {sec['budget_chars']} 字" if sec["budget_chars"] else "预算未声明"
        lines.append(f"## {sec['oid']} {sec['title']}（{bud}）")
        lines.append(f"- 论证任务：{sec['question']}")
        if sec["required_elements"]:
            lines.append(f"- 必备要素：{'；'.join(sec['required_elements'])}")
        if sec["coverage"]:
            lines.append(f"- 证据来源（材料段落）：{', '.join(sec['evidence_pids'][:8])}")
            for h in sec["coverage"][:3]:
                lines.append(f"  - {h['pid']}（{h['section_title']}，相关度 {h['score']}）：{h['excerpt']}")
        else:
            lines.append("- 证据来源：暂无匹配材料段落（需补充材料或人工确认）")
        lines.append(f"- 覆盖状态：{sec['coverage_status']}")
        lines.append("")
    with open(os.path.join(args.work, "outline.json"), "w", encoding="utf-8") as f:
        json.dump(outline, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.work, "chapter_plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.work, "chapter_plan.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    # coverage_report.md
    rl = ["# 覆盖与缺口报告", ""]
    rl.append(f"大纲条目 {len(entries)} 个；材料未覆盖段落 {len(gaps)} 段；疑似重复章节对 {len(pairs)} 对。")
    rl.append("")
    if pairs:
        rl.append("## 章节重复风险")
        for p in pairs:
            rl.append(f"- {p['oids'][0]}《{p['titles'][0]}》 ↔ {p['oids'][1]}《{p['titles'][1]}》：材料重叠 {p['overlap_ratio']}")
        rl.append("")
    if gaps:
        rl.append("## 材料缺口（未映射到任何大纲条目的材料）")
        for g in gaps[:20]:
            rl.append(f"- {g['pid']}（{g['sid']}）：{g['excerpt']}")
        rl.append("")
    missing_el = [k for k, v in elements_ok.items() if not v]
    rl.append("## 必备论证要素完整性")
    for k, v in elements_ok.items():
        rl.append(f"- {'✓' if v else '✗'} {k}")
    if missing_el:
        rl.append(f"> ⚠ 大纲未显式承接的要素：{'、'.join(missing_el)}（写作时须补充或在 uncertainty 登记）")
    with open(os.path.join(args.work, "coverage_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(rl))
    print(f"[outline_engine plan] 大纲条目 {len(entries)}，材料段落 {chapters.get('n_paragraphs', 0)}，"
          f"缺口 {len(gaps)}，重复对 {len(pairs)}，要素缺失 {missing_el}")
    return 0

def cmd_check(args):
    plan = load_json(args.plan, {}) or {}
    chapters = load_json(args.chapters, {}) or {}
    try:
        with open(args.chapter, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        print(f"[outline_engine] 章节读取失败: {e}", file=sys.stderr)
        return 1
    n_chars = len(re.sub(r"\s+", "", text))
    headings = [(m.start(), m.group(0)) for m in re.finditer(
        r"^#{1,6}\s+.+$|^(第[一二三四五六七八九十\d]+[章节]\s*\S.*|\d+(?:\.\d+){0,3}\s*[\u4e00-\u9fff].+)$",
        text, re.M)]
    numbers = re.findall(r"^#{1,6}\s+(\d+(?:\.\d+){0,3})", text, re.M)
    seq_ok = True
    if numbers:
        flat = [int(n.replace(".", "")) for n in numbers]
        seq_ok = all(flat[i] < flat[i + 1] for i in range(len(flat) - 1))
    # 篇幅：匹配最接近的大纲条目
    target = None
    for sec in plan.get("sections", []):
        if sec["title"] and sec["title"].split("（")[0][:4] in text:
            target = sec
            break
    budget = (target or {}).get("budget_chars")
    deviation = round(n_chars / budget - 1, 3) if budget else None
    if target and target.get("required_elements"):
        present = {el: any(w in text for w in [el] + REQUIRED_ELEMENTS.get(el, []))
                   for el in target["required_elements"]}
    else:
        present = {k: any(w in text for w in words) for k, words in REQUIRED_ELEMENTS.items()}
    issues, warns = [], []
    if not seq_ok:
        issues.append("章节编号不连续或逆序")
    for k, v in present.items():
        if not v:
            warns.append(f"必备要素缺失：{k}")
    if deviation is not None:
        if abs(deviation) > 0.5:
            issues.append(f"篇幅偏差 {deviation:+.0%}（预算 {budget} 字，实际 {n_chars} 字）")
        elif abs(deviation) > 0.25:
            warns.append(f"篇幅偏差 {deviation:+.0%}（预算 {budget}，实际 {n_chars}）")
    materials_text = ""
    if args.materials and os.path.exists(args.materials):
        try:
            with open(args.materials, encoding="utf-8") as f:
                materials_text = f.read()
        except Exception:
            pass
    numbers_report = numbers_traceable(text, materials_text) if materials_text else []
    unverified = [n for n in numbers_report if n["status"] == "unverified"]
    if unverified:
        warns.append(f"{len(unverified)} 个数值无法溯源到材料："
                     f"{[n['raw'] for n in unverified[:10]]}（已登记 uncertainty，不得臆造来源）")
    check = {"chapter_file": args.chapter, "char_count": n_chars,
             "target_outline_oid": (target or {}).get("oid"),
             "budget_chars": budget, "budget_deviation": deviation,
             "heading_sequence_ok": seq_ok,
             "required_elements": present,
             "issues": issues, "warnings": warns,
             "numbers": numbers_report}
    with open(os.path.join(args.work, "chapter_check.json"), "w", encoding="utf-8") as f:
        json.dump(check, f, ensure_ascii=False, indent=2)
    print(f"[outline_engine check] {n_chars} 字，偏差 {deviation}，要素缺失 "
          f"{[k for k, v in present.items() if not v]}，数值未溯源 {len(unverified)}")
    return 0

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("plan")
    p1.add_argument("--chapters", required=True)
    p1.add_argument("--outline", required=True)
    p1.add_argument("--materials", default=None)
    p1.add_argument("--work", default="/app/work")
    p1 = None
    sub.choices["plan"].set_defaults(func=cmd_plan)
    p2 = sub.add_parser("check")
    p2.add_argument("--chapter", required=True)
    p2.add_argument("--chapters", required=True)
    p2.add_argument("--plan", required=True)
    p2.add_argument("--materials", default=None)
    p2.add_argument("--work", default="/app/work")
    sub.choices["check"].set_defaults(func=cmd_check)
    args = ap.parse_args()
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
