#!/usr/bin/env python3
"""report_builder.py — 汇总机检 findings 与覆盖率统计，生成翻译质量报告 report.md
与机读 edit_plan.json（供作者逐条采纳/驳回）。

用法: python3 report_builder.py --work /app/work --out /app/output \
        --focus terminology --skill "<name> vX.Y.Z"
findings.json 统一 schema：{id, dimension, type, location{seg_id,section}, quote,
evidence, action{op,instruction}, severity(高/中/低), confidence, status}
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trans_utils as tu

FOCUS_NAME = {
    "terminology": "术语一致性", "numbers": "事实与数字", "alignment": "双语对齐",
    "style": "学术风格", "boundary": "引用保留与语义边界",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--focus", required=True)
    ap.add_argument("--skill", required=True)
    args = ap.parse_args()

    insp = tu.load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    stats = tu.load_json(os.path.join(args.work, "stats.json"), {}) or {}
    findings = tu.load_json(os.path.join(args.work, "findings.json"), []) or []
    uncertainty = tu.load_json(os.path.join(args.work, "uncertainty.json"), []) or []
    tt = insp.get("translation_task") or {}

    sev_order = {"高": 0, "中": 1, "低": 2}
    findings.sort(key=lambda x: (sev_order.get(x.get("severity"), 3),
                                 x.get("location", {}).get("seg_id", "")))
    tu.save_json(os.path.join(args.out, "findings.json"), findings)

    edit_plan = [{
        "id": f.get("id"), "location": f.get("location"),
        "op": (f.get("action") or {}).get("op"),
        "instruction": (f.get("action") or {}).get("instruction"),
        "severity": f.get("severity"), "status": f.get("status", "待作者复核"),
    } for f in findings]
    tu.save_json(os.path.join(args.out, "edit_plan.json"), edit_plan)

    by_sev = {"高": 0, "中": 0, "低": 0}
    for f in findings:
        by_sev[f.get("severity", "低")] = by_sev.get(f.get("severity", "低"), 0) + 1

    L = []
    L.append(f"# 翻译质量报告 — {FOCUS_NAME.get(args.focus, args.focus)}方向")
    L.append("")
    L.append(f"- Skill：{args.skill}")
    L.append(f"- case_id：{insp.get('case_id')}")
    L.append(f"- 翻译方向：{tt.get('direction')}（目标语 {tt.get('target_lang')}）；"
             f"交付形态：{tt.get('output_form')}")
    L.append(f"- 覆盖率：{stats.get('segments_translated', 0)}/"
             f"{stats.get('segments_need_translation', 0)} 句段 "
             f"（{stats.get('coverage', 0):.1%}）；受保护片段 "
             f"{stats.get('protected_spans_total', 0)} 处")
    L.append(f"- 机检发现：高严重度 {by_sev['高']} 项 / 中 {by_sev['中']} 项 / 低 {by_sev['低']} 项；"
             f"不确定性记录 {len(uncertainty)} 条")
    L.append("")
    L.append("> 本报告问题均为脚本机检候选 + Agent 复核结果；每条含原文锚点、"
             "依据与可执行修订指令。未检出问题的维度以统计字段说明，不虚构缺陷。")
    L.append("")
    L.append("## 问题清单")
    L.append("")
    if not findings:
        L.append("（机检未发现该方向问题；如稿件本身无此类问题属正常结论。）")
    for f in findings:
        loc = f.get("location") or {}
        act = f.get("action") or {}
        L.append(f"### {f.get('id')} 〔{f.get('severity')}·{f.get('type')}〕 "
                 f"{loc.get('seg_id', '')}（{loc.get('section') or ''}）")
        L.append("")
        L.append(f"- 原文锚点：{f.get('quote', '')}")
        L.append(f"- 机检依据：{f.get('evidence', '')}")
        L.append(f"- 修订指令（{act.get('op', '')}）：{act.get('instruction', '')}")
        L.append(f"- 置信度 {f.get('confidence', '')}；状态：{f.get('status', '')}")
        L.append("")
    if uncertainty:
        L.append("## 不确定性与人工确认项")
        L.append("")
        for u in uncertainty[:60]:
            L.append(f"- [{u.get('kind')}] {u.get('seg_id') or u.get('location') or ''} "
                     f"{u.get('note')}")
        L.append("")
    with open(os.path.join(args.out, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"[report_builder] findings={len(findings)} "
          f"高/中/低={by_sev['高']}/{by_sev['中']}/{by_sev['低']} → report.md + edit_plan.json")
    return 0

if __name__ == "__main__":
    sys.exit(main())
