#!/usr/bin/env python3
"""report_builder.py — 汇总扫描与引擎 findings，生成可交付草稿：
  /app/output/diagnosis_report.md  结构化诊断报告（作者可逐条复核：采纳/部分采纳/驳回）
  /app/output/edit_plan.json       机读编辑动作清单（move/merge/split/narrow/add_*）
  /app/output/findings.json        全部问题（统一 schema，去重后）
  work/evidence_map.json           证据→原文位置映射
  work/stats.json / work/uncertainty.json
Agent 可在本草稿基础上做判断性修订（删误报、补漏报、调优先级）。
"""
import argparse, json, os, sys, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scanutil import short

DIM_NAMES = {
    "research_question": "研究问题与贡献对齐",
    "section_structure": "章节结构与叙事顺序",
    "argument_chain": "论证链与论据对应",
    "paragraph_relation": "段落关系与衔接",
    "redundancy": "重复内容",
    "conclusion_boundary": "结论边界与表述尺度",
}
SEV_ORDER = {"high": 0, "medium": 1, "low": 2}

def load(work, name, default):
    p = os.path.join(work, name)
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def dedup(findings):
    seen, out = set(), []
    for f in findings:
        key = (f.get("dimension"), f.get("type"),
               (f.get("location") or {}).get("para_id"),
               (f.get("location") or {}).get("sentence_id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    out.sort(key=lambda f: (SEV_ORDER.get(f.get("severity"), 3), f.get("id", "")))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--focus", default="", help="本版本主攻维度（报告中置顶详述）")
    ap.add_argument("--skill", default="structure-skill")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    model = load(args.work, "structure.json", {})
    insp = load(args.work, "inspection.json", {})
    findings = dedup(load(args.work, "findings_scan.json", [])
                     + load(args.work, "findings_engine.json", []))

    # 重新编号（保持维度前缀）
    counters = collections.Counter()
    for f in findings:
        dim_code = {"research_question": "D1", "section_structure": "D2",
                    "argument_chain": "D3", "paragraph_relation": "D4",
                    "redundancy": "D5", "conclusion_boundary": "D6"}.get(f["dimension"], "DX")
        counters[dim_code] += 1
        f["id"] = f"{dim_code}-{counters[dim_code]:02d}"

    # findings.json + edit_plan.json
    with open(os.path.join(args.out, "findings.json"), "w", encoding="utf-8") as fp:
        json.dump(findings, fp, ensure_ascii=False, indent=1)
    edit_plan = {
        "plan_id": f"edit-plan-{insp.get('case_id') or 'unknown'}",
        "generated_by": args.skill,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "usage": "按 severity 顺序执行；每条 op 对应 findings.json 同 id 问题；执行后逐项勾选采纳/部分采纳/驳回。",
        "ops": [{
            "op_id": f["id"], "op": f["action"]["op"], "instruction": f["action"]["instruction"],
            "target": f["location"], "anchor_quote": f["quote"],
            "rationale": f["evidence"], "severity": f["severity"],
            "confidence": f["confidence"], "review_status": "待作者复核",
        } for f in findings],
    }
    with open(os.path.join(args.out, "edit_plan.json"), "w", encoding="utf-8") as fp:
        json.dump(edit_plan, fp, ensure_ascii=False, indent=1)

    # evidence_map / stats / uncertainty
    evidence_map = [{
        "claim": f"{f['id']} {f['type']}", "dimension": f["dimension"],
        "source_location": f["location"], "anchor_quote": f["quote"],
        "evidence": f["evidence"], "verifiable": True,
    } for f in findings]
    with open(os.path.join(args.work, "evidence_map.json"), "w", encoding="utf-8") as fp:
        json.dump(evidence_map, fp, ensure_ascii=False, indent=1)

    st = model.get("stats", {})
    by_dim = collections.Counter(f["dimension"] for f in findings)
    by_sev = collections.Counter(f["severity"] for f in findings)
    stats = {"manuscript": st, "n_findings": len(findings),
             "findings_by_dimension": dict(by_dim), "findings_by_severity": dict(by_sev),
             "dimensions_covered": sorted(by_dim.keys())}
    with open(os.path.join(args.work, "stats.json"), "w", encoding="utf-8") as fp:
        json.dump(stats, fp, ensure_ascii=False, indent=1)

    uncertainty = []
    for iss in (model.get("issues") or []) + (insp.get("issues") or []):
        uncertainty.append({"item": iss, "impact": "相关维度判断置信度下调，需人工复核",
                            "source": "pipeline"})
    low_conf = [f for f in findings if f.get("confidence", 1) < 0.6]
    for f in low_conf:
        uncertainty.append({"item": f"{f['id']} {f['type']}",
                            "impact": "启发式规则置信度<0.6，可能是误报，需作者复核",
                            "source": "heuristic"})
    with open(os.path.join(args.work, "uncertainty.json"), "w", encoding="utf-8") as fp:
        json.dump(uncertainty, fp, ensure_ascii=False, indent=1)

    # diagnosis_report.md
    L = []
    L.append(f"# 论文结构与逻辑诊断报告\n")
    L.append(f"- 案例标识: {insp.get('case_id') or 'unknown'}")
    L.append(f"- 稿件: {os.path.basename(model.get('source_file') or '?')} "
             f"（{model.get('format', '?')}；章节 {st.get('n_sections', 0)} / "
             f"段落 {st.get('n_paragraphs', 0)} / 句子 {st.get('n_sentences', 0)} / "
             f"字符 {st.get('n_chars', 0)}）")
    L.append(f"- 诊断维度: 六维全覆盖（研究问题 / 章节结构 / 论证链 / 段落关系 / 重复内容 / 结论边界）"
             + (f"；本技能主攻：**{DIM_NAMES.get(args.focus, args.focus)}**" if args.focus else ""))
    L.append(f"- 问题总数: {len(findings)}（高 {by_sev.get('high', 0)} / 中 {by_sev.get('medium', 0)} / "
             f"低 {by_sev.get('low', 0)}）；机读编辑计划见 edit_plan.json")
    L.append(f"- 生成时间: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n")
    if uncertainty:
        L.append("## 0. 材料缺口与不确定性（先于结论阅读）\n")
        for u in uncertainty[:12]:
            L.append(f"- {u['item']} → {u['impact']}")
        L.append("")
    all_dims = sorted(DIM_NAMES.keys(), key=lambda d: (d != args.focus, d))
    for dim in all_dims:
        items = [f for f in findings if f["dimension"] == dim]
        L.append(f"## {DIM_NAMES.get(dim, dim)}（{len(items)} 条）\n")
        if not items:
            L.append("本维度未检出结构性问题。说明：六维普查与主攻引擎均覆盖此维度；"
                     "未检出不代表绝无问题——阈值内候选见 work/findings_scan.json，"
                     "且启发式规则无法替代人工通读。\n")
        for f in items:
            loc = f["location"]
            loc_str = " › ".join(x for x in [loc.get("section"), loc.get("para_id"),
                                             loc.get("sentence_id")] if x)
            L.append(f"### [{f['id']}] {f['type']}（严重度 {f['severity']} / 置信度 {f['confidence']}）\n")
            L.append(f"- **位置**: {loc_str or '(全文)'}")
            L.append(f"- **原文锚点**: “{f['quote']}”")
            L.append(f"- **判断依据**: {f['evidence']}")
            L.append(f"- **编辑动作** (`{f['action']['op']}`): {f['action']['instruction']}")
            L.append(f"- **复核状态**: {f['status']}（采纳 / 部分采纳 / 驳回）\n")
    L.append("## 复核与使用说明\n")
    L.append("- 每条问题均可按 `位置 + 原文锚点` 指回原文独立复核；`置信度<0.6` 的条目为启发式候选，优先人工确认。")
    L.append("- `edit_plan.json` 为机读编辑动作清单，op 类型：move / merge / split / narrow / qualify / "
             "add / add_transition / add_limitation / reorder。")
    L.append("- 本报告不新增稿件外事实；所有数字、引用、图表锚点均来自原文定位。")
    with open(os.path.join(args.out, "diagnosis_report.md"), "w", encoding="utf-8") as fp:
        fp.write("\n".join(L))

    print(f"[report_builder] findings={len(findings)} 维度={dict(by_dim)} "
          f"-> diagnosis_report.md / edit_plan.json / findings.json")
    return 0

if __name__ == "__main__":
    sys.exit(main())
