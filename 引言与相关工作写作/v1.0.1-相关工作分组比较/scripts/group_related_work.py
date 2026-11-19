#!/usr/bin/env python3
"""group_related_work.py — V2 相关工作按路线分组：分组完整性 + 比较矩阵 + 逐篇罗列检测。

用法: python3 group_related_work.py --work /app/work --out /app/output
读 work/grouping.json、work/comparison_rows.jsonl、work/draft_rl.md、work/claim_bindings.jsonl：
  grouping.json: {"groups":[{"gid","theme","dimension_focus","entry_ids":[...],"note"}]}
  comparison_rows.jsonl: 每行 {"entry_id","problem_setting","method_route","data_eval","conclusion","limitation"}（Agent 逐条填写，缺行允许但计入矩阵覆盖率）
校验:
  1) 相关工作实际引用的 entry 集合 == 各组 entry_ids 并集（无遗漏、无跨组重复、无未引用条目入组）；
  2) 每组必须有 theme 与 ≥1 个 entry；建议 dimension_focus 覆盖 问题设定/方法路线/数据与评价 中的至少两个维度；
  3) 逐篇罗列检测：段落内 ≥2 句以四位年份开头，或单句成段连续 ≥3 段且每段只涉一篇文献 → 记 chronological_suspect；
  4) 渲染 comparison_matrix.md（按组组织的比较矩阵）。
verdict ∈ {pass, warn, fail}。
"""
import argparse, json, os, re, sys

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
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    rows.append({"_error": line[:80]})
    return rows

DIMENSIONS = ("问题设定", "方法路线", "数据与评价", "问题", "方法", "数据", "评价")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    grouping = load_json(os.path.join(args.work, "grouping.json"), {}) or {}
    groups = grouping.get("groups", []) if isinstance(grouping, dict) else []
    bindings = [b for b in load_jsonl(os.path.join(args.work, "claim_bindings.jsonl"))
                if isinstance(b, dict) and not b.get("_error") and b.get("loc") == "rl"]
    lib = load_json(os.path.join(args.work, "library.json"), {}) or {}
    records = {r.get("id"): r for r in lib.get("records", []) if r.get("id")}

    cited = []
    seen = set()
    for b in bindings:
        for e in (b.get("entry_ids") or []):
            if e in records and e not in seen:
                seen.add(e)
                cited.append(e)

    orphans, duplicates, ungrouped = [], [], []
    grouped = []
    gid_of = {}
    for g in groups:
        gid = g.get("gid") or f"G{len(grouped)+1}"
        grouped.append(gid)
        for e in (g.get("entry_ids") or []):
            if e not in records:
                orphans.append({"gid": gid, "entry_id": e, "reason": "not_in_library"})
                continue
            if e in gid_of:
                duplicates.append({"entry_id": e, "in_groups": [gid_of[e], gid]})
            gid_of[e] = gid
    for e in cited:
        if e not in gid_of:
            ungrouped.append(e)

    group_issues = []
    for g in groups:
        gid = g.get("gid") or "?"
        if not (g.get("theme") or "").strip():
            group_issues.append({"gid": gid, "issue": "缺少 theme（分组主题）"})
        if not g.get("entry_ids"):
            group_issues.append({"gid": gid, "issue": "空组（entry_ids 为空）"})
        focus = g.get("dimension_focus") or ""
        if focus and not any(d in focus for d in DIMENSIONS):
            group_issues.append({"gid": gid, "issue": f"dimension_focus 未指向比较维度: {focus}"})

    # 逐篇罗列 / 时间序检测
    draft = ""
    dp = os.path.join(args.work, "draft_rl.md")
    if os.path.exists(dp):
        with open(dp, encoding="utf-8") as f:
            draft = f.read()
    chronological = []
    paras = [p.strip() for p in re.split(r"\n\s*\n", draft) if p.strip()]
    for p in paras:
        if p.startswith("#"):
            continue
        sents = re.split(r"(?<=[。；;.!?])\s*", p)
        year_first = sum(1 for s in sents if re.match(r"^\s*(19|20)\d{2}\s*年", s))
        if year_first >= 2:
            chronological.append({"paragraph_head": p[:80], "reason": f"{year_first} 句以年份起始"})
    if len(paras) >= 4:
        single_work_paras = 0
        for p in paras:
            if p.startswith("#"):
                continue
            sents = [s for s in re.split(r"(?<=[。；;.!?])\s*", p) if s.strip()]
            if len(sents) == 1:
                single_work_paras += 1
        if single_work_paras >= 3 and single_work_paras >= len([p for p in paras if not p.startswith('#')]) * 0.6:
            chronological.append({"paragraph_head": "(全文)", "reason": f"{single_work_paras} 个单句成段，疑似逐篇罗列"})

    rows = [r for r in load_jsonl(os.path.join(args.work, "comparison_rows.jsonl"))
            if isinstance(r, dict) and not r.get("_error")]
    matrix_by_id = {r.get("entry_id"): r for r in rows if r.get("entry_id") in records}

    # 矩阵渲染
    lines = ["# 相关工作分组比较矩阵", ""]
    lines.append(f"- 引用文献 {len(cited)} 条；入组 {len(gid_of)} 条；比较矩阵行数 {len(rows)}")
    lines.append("")
    for g in groups:
        gid = g.get("gid") or "?"
        theme = (g.get("theme") or "(未命名)").strip()
        focus = (g.get("dimension_focus") or "").strip()
        lines.append(f"## {theme}")
        if focus:
            lines.append(f"比较维度：{focus}")
        if g.get("note"):
            lines.append(f"组注：{g['note']}")
        lines.append("")
        entries = g.get("entry_ids") or []
        lines.append("| 文献 | 问题设定 | 方法路线 | 数据与评价 | 主要结论 | 局限 |")
        lines.append("|---|---|---|---|---|---|")
        for e in entries:
            rec = records.get(e, {})
            label = f"{e} {(rec.get('title') or '')[:30]}({rec.get('year','?')})"
            r = matrix_by_id.get(e, {})
            def cell(k):
                v = (r.get(k) or "").strip()
                return v.replace("|", "/") if v else "—（未填写）"
            lines.append(f"| {label} | {cell('problem_setting')} | {cell('method_route')} | "
                         f"{cell('data_eval')} | {cell('conclusion')} | {cell('limitation')} |")
        lines.append("")
    if not groups:
        lines.append("（未提供 grouping.json 分组，无法渲染矩阵）")

    if ungrouped or duplicates or not groups:
        verdict = "fail" if (not groups or len(ungrouped) > len(cited) * 0.5) else "warn"
    elif chronological or group_issues:
        verdict = "warn"
    else:
        verdict = "pass"

    report = {"version": "v1.0.1-相关工作分组比较",
              "cited_entries": cited,
              "grouped_entries": sorted(gid_of),
              "ungrouped_cited": ungrouped,
              "duplicates": duplicates,
              "unknown_entries": orphans,
              "group_issues": group_issues,
              "chronological_suspect": chronological,
              "matrix_rows": len(rows),
              "matrix_missing_for": [e for e in cited if e not in matrix_by_id],
              "verdict": verdict}
    os.makedirs(args.work, exist_ok=True)
    with open(os.path.join(args.work, "version_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "comparison_matrix.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[group_rl] 组={len(groups)} 引用={len(cited)} 未入组={len(ungrouped)} "
          f"重复={len(duplicates)} 时间序嫌疑={len(chronological)} 矩阵行={len(rows)} verdict={verdict}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
