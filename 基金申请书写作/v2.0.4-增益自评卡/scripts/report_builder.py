#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_builder.py --work W --out O --focus <slug> --skill "name vX.Y.Z"

汇总 inspection/stats/各 findings/exceptions/uncertainty/manual_confirmations
→ O/report.md（中文）。同时写 work/stats.json。
"""
import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu

STAGE = "report_builder"

SCRIPT_LABOR = [
    ("init_result.py", "初始化 result.json 骨架并预填 output_contract 字段"),
    ("inspect_case.py", "解析 case/task/workorder，识别要素与交付约束"),
    ("parse_materials.py", "抽取全部材料文本并分段编号（F1-P001）"),
    ("fact_ledger.py", "抽取数字/引用/成果/术语台账并去重编号（F0001）"),
    ("draft_builder.py", "组装章节稿，校验证据标记存在性，出清洁/留痕两版"),
    ("source_audit.py", "机检材料外数字/引用与不可核验修饰词"),
    ("elements_check.py", "七要素覆盖与厚度检查，出三级对应表"),
    ("elements_check.py(对照)", "生成 element_mapping.md 要素对照说明"),
    ("assemble_result.py", "回填 result.json 契约字段与 evidence_map"),
    ("validate_output.py", "发布闸门：逐项 PASS/FAIL 校验"),
    ("render_previews.py", "生成 preview.html，尽力渲染 preview.pdf"),
]


def load_work_json(work, name, default):
    return gu.read_json(os.path.join(work, name), default)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--focus", default="grant-writing")
    ap.add_argument("--skill", default="grant-writing")
    args = ap.parse_args()
    work, out = args.work, gu.env_output_dir(args.out)
    gu.ensure_dir(work)
    gu.ensure_dir(out)

    inspection = load_work_json(work, "inspection.json", {}) or {}
    materials = load_work_json(work, "materials.json", {}) or {}
    ledger = load_work_json(work, "fact_ledger.json", {"entries": []}) or {}
    draft = load_work_json(work, "draft.json", {"paragraphs": []}) or {}
    element_map = load_work_json(work, "element_map.json", {}) or {}
    exceptions = load_work_json(work, "exceptions.json", []) or []
    uncertainty = load_work_json(work, "uncertainty.json", {}) or {}
    manual = load_work_json(work, "manual_confirmations.json", []) or []
    findings_files = ["findings_draft.json", "source_audit.json",
                      "element_findings.json", "findings.json"]
    all_findings = []
    for name in findings_files:
        data = load_work_json(work, name, None)
        if isinstance(data, list):
            for x in data:
                if isinstance(x, dict):
                    x = dict(x)
                    x.setdefault("source_file", name)
                    all_findings.append(x)
        elif isinstance(data, dict) and isinstance(data.get("findings"), list):
            for x in data["findings"]:
                if isinstance(x, dict):
                    x = dict(x)
                    x.setdefault("source_file", name)
                    all_findings.append(x)

    sev_counter = Counter(x.get("severity", "unknown") for x in all_findings)
    kind_counter = Counter(x.get("kind", "unknown") for x in all_findings)
    paragraphs = draft.get("paragraphs", [])
    covered = sum(1 for m in element_map.values() if m.get("dpids"))
    ok = sum(1 for m in element_map.values() if m.get("status") == "ok")
    entries = ledger.get("entries", [])

    stats = {
        "paragraphs": len(paragraphs),
        "elements_required": len(inspection.get("required_elements") or []),
        "elements_covered": covered,
        "elements_ok": ok,
        "findings_total": len(all_findings),
        "findings_by_severity": dict(sev_counter),
        "ledger_entries": len(entries),
        "material_files": (materials.get("stats") or {}).get("files", 0),
        "exceptions": len(exceptions),
    }
    gu.write_json(os.path.join(work, "stats.json"), stats)

    L = ["# 质量报告（report）", "",
         f"- Skill：`{args.skill}`（focus: {args.focus}）",
         f"- case_id：`{inspection.get('case_id', 'unknown')}`",
         f"- 材料文件：{stats['material_files']} 个；台账条目：{len(entries)} 条；"
         f"草稿段落：{len(paragraphs)} 段", ""]
    L += ["## 一、任务与交付", ""]
    hints = inspection.get("deliverable_hints") or {}
    if hints:
        L.append(f"- 交付线索：{hints}")
    L += [f"- 产物：proposal_draft.md（清洁稿）、proposal_annotated.md（留痕稿）、"
          "element_mapping.md（要素对照）、report.md（本报告）、"
          "result.json（结构化结果）、preview.html（预览）", ""]
    L += ["## 二、七要素覆盖表", "",
          "| 要素 | 段落数 | 字数 | 证据数 | 状态 |", "|---|---|---|---|---|"]
    for e, m in element_map.items():
        L.append(f"| {e} | {len(m.get('dpids', []))} | {m.get('chars', 0)} | "
                 f"{len(m.get('fids', []))} | {m.get('status', '?')} |")
    L += ["", f"要素覆盖 {covered}/{len(element_map)}，达标 {ok}/{len(element_map)}。", ""]
    L += ["## 三、专项审计摘要（findings 分级统计）", ""]
    if all_findings:
        L.append(f"- 按级别：{dict(sev_counter)}")
        L.append(f"- 按类型：{dict(kind_counter)}")
        L.append("")
        L += ["| 级别 | 类型 | 段落/要素 | 说明 |", "|---|---|---|---|"]
        for x in all_findings[:80]:
            loc = x.get("dpid") or x.get("element") or "-"
            L.append(f"| {x.get('severity','?')} | {x.get('kind','?')} | {loc} | "
                     f"{str(x.get('msg',''))[:80]} |")
        if len(all_findings) > 80:
            L.append(f"\n（其余 {len(all_findings) - 80} 条见 work/ 下各 findings json）")
    else:
        L.append("未发现 finding。")
    L += ["", "## 四、来源与核验统计", "",
          f"- 事实台账：{len(entries)} 条（"
          + "、".join(f"{t}:{c}" for t, c in
                      Counter(e.get('type') for e in entries).items()) + "）",
          f"- 证据标记：{(draft.get('markers_summary') or {}).get('fid_refs', 0)} 处〔F〕、"
          f"{(draft.get('markers_summary') or {}).get('planned', 0)} 处〔拟〕、"
          f"{(draft.get('markers_summary') or {}).get('confirm', 0)} 处〔确认〕",
          f"- 运行异常：{len(exceptions)} 条（见 result.json exceptions）", ""]
    L += ["## 五、异常与限制", ""]
    if exceptions:
        for x in exceptions[:20]:
            L.append(f"- [{x.get('stage')}] {x.get('file')}: {x.get('error')} → {x.get('action')}")
    else:
        L.append("- 无运行异常。")
    if uncertainty:
        L.append(f"- 不确定性：{uncertainty}")
    if manual:
        L.append(f"- 需人工确认 {len(manual)} 项：{manual[:10]}")
    L += ["- 机检限制：source_audit 只做值级比对（±0 容差、单位等价），"
          "不做语义改写判断；修饰词扫描基于固定词表。", ""]
    L += ["## 六、效率说明（脚本承担的机械劳动）", ""]
    for name, desc in SCRIPT_LABOR:
        L.append(f"- `{name}`：{desc}")
    L.append("")
    L += ["> 本报告由 report_builder.py 自动汇总生成；评分以实际产物为准。", ""]

    report_path = os.path.join(out, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    # v2.0.4 补丁：若 gain_card.py 已生成 O/gain_card.md，末尾追加"增益自评卡"节；
    # 不存在则行为与父辈完全一致。
    gain_card_path = os.path.join(out, "gain_card.md")
    if os.path.isfile(gain_card_path):
        try:
            with open(gain_card_path, "r", encoding="utf-8") as f:
                gain_text = f.read().strip()
            if gain_text:
                with open(report_path, "a", encoding="utf-8") as f:
                    f.write("\n## 增益自评卡\n\n" + gain_text + "\n")
        except Exception as e:
            print(f"[report_builder] WARN: gain_card 嵌入失败（忽略）：{e}")
    print(f"[report_builder] findings={len(all_findings)} "
          f"stats={stats['paragraphs']}p/{len(entries)}f")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[report_builder] ERROR: {e}")
        raise SystemExit(1)
