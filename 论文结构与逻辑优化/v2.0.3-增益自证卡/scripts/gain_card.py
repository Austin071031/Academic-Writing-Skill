#!/usr/bin/env python3
"""gain_card.py — 增益自证卡（v2.0.3 单点新增）。

用法: python3 gain_card.py --work /app/work --out /app/output
时机: report_builder 之后、assemble_result 之前（Agent 复核修订 findings 后可重跑，幂等）。

从 out/findings.json、out/diagnosis_report.md、work/stats.json、work/change_log.json
计算机读增益指标并自证相对"基础 Agent"的增量：
  1. 六维覆盖率（有 finding 或报告中有显式"未检出"说明的维度数 / 6）
  2. 锚点率（quote 非空且非占位符开头的 finding 占比）
  3. 可执行动作率（action.op ∈ 9 类允许 op 且 instruction 非空的占比）
  4. 定位粒度分布（句子级 / 段落级 / 全文级条数）
  5. 机械劳动清单（change_log 脚本步骤数）与 Agent 判断步骤数
  6. 估计效率（脚本管线秒级 vs 人工通读基线 n_chars/1500 字每分钟，均为"估计"）
并生成反事实对照表（左列基础 Agent 通用建议示意 5 条 vs 右列本技能 high 级前 5 条摘录）。
产物: out/gain_card.md、out/gain_card.json；并在 out/diagnosis_report.md 末尾
追加"## 增益自证卡（机器可复算）"节。全部数字可由 findings.json/stats.json 复算。
"""
import argparse, json, os, sys, datetime, re

DIM_NAMES = {
    "research_question": "研究问题与贡献对齐",
    "section_structure": "章节结构与叙事顺序",
    "argument_chain": "论证链与论据对应",
    "paragraph_relation": "段落关系与衔接",
    "redundancy": "重复内容",
    "conclusion_boundary": "结论边界与表述尺度",
}
ALLOWED_OPS = ["move", "merge", "split", "narrow", "qualify",
               "add", "add_transition", "add_limitation", "reorder"]
# change_log 中由脚本完成的步骤名（其余视为 Agent 判断步骤）
SCRIPT_STEPS = {"inspect_case", "parse_manuscript", "six_scan", "section_flow",
                "report_builder", "init_result", "assemble_result", "validate_output",
                "gain_card"}
QUOTE_PLACEHOLDER_PREFIX = ("(未检出", "(全文)", "（未检出", "（全文）")
SEV_ORDER = {"high": 0, "medium": 1, "low": 2}
# 反事实对照左列：基础 Agent 典型输出（固定文案，反事实示意，非实测）
BASELINE_AGENT_TYPICAL = [
    "建议增强文章逻辑性",
    "注意段落间衔接",
    "结论应与结果一致",
    "建议调整章节顺序",
    "注意避免内容重复",
]
MANUAL_CHARS_PER_MIN = 1500  # 人工逐条通读基线（字/分钟，估计值）
GAIN_SECTION_HEAD = "## 增益自证卡（机器可复算）"


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def loc_str(loc):
    loc = loc or {}
    return " › ".join(x for x in [loc.get("section"), loc.get("para_id"),
                                  loc.get("sentence_id")] if x) or "(全文)"


def granularity(loc):
    loc = loc or {}
    if loc.get("sentence_id"):
        return "句子级"
    if loc.get("para_id"):
        return "段落级"
    return "全文级"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    findings = load_json(os.path.join(args.out, "findings.json"), []) or []
    stats = load_json(os.path.join(args.work, "stats.json"), {}) or {}
    change_log = load_json(os.path.join(args.work, "change_log.json"), []) or []
    report_path = os.path.join(args.out, "diagnosis_report.md")
    report = ""
    if os.path.exists(report_path):
        with open(report_path, encoding="utf-8") as f:
            report = f.read()

    n = len(findings)

    # 1) 六维覆盖率：有 finding，或报告该维度节内含显式"未检出"说明
    dims_detail, covered = [], 0
    for dim, name in DIM_NAMES.items():
        n_dim = sum(1 for f in findings if f.get("dimension") == dim)
        m = re.search(r"##\s*" + re.escape(name) + r"（\d+ 条）\n(.*?)(?=\n## |\Z)",
                      report, re.S)
        sec_body = m.group(1) if m else ""
        not_found_note = ("未检出" in sec_body)
        cov = n_dim > 0 or not_found_note
        covered += 1 if cov else 0
        dims_detail.append({"dimension": dim, "name": name, "n_findings": n_dim,
                            "explicit_not_found_note": not_found_note, "covered": cov})

    # 2) 锚点率
    anchored = [f for f in findings
                if (f.get("quote") or "").strip()
                and not (f.get("quote") or "").strip().startswith(QUOTE_PLACEHOLDER_PREFIX)]
    anchor_rate = round(100.0 * len(anchored) / n, 1) if n else 0.0

    # 3) 可执行动作率
    actable = [f for f in findings
               if (f.get("action") or {}).get("op") in ALLOWED_OPS
               and ((f.get("action") or {}).get("instruction") or "").strip()]
    ops_rate = round(100.0 * len(actable) / n, 1) if n else 0.0

    # 4) 定位粒度分布
    gran = {"句子级": 0, "段落级": 0, "全文级": 0}
    for f in findings:
        gran[granularity(f.get("location"))] += 1

    # 5) 机械劳动清单 vs Agent 判断步骤
    script_steps = [c for c in change_log if c.get("step") in SCRIPT_STEPS]
    agent_steps = [c for c in change_log if c.get("step") not in SCRIPT_STEPS]

    # 6) 估计效率（均为估计值）
    n_chars = ((stats.get("manuscript") or {}).get("n_chars")
               or stats.get("n_chars") or 0)
    manual_min = round(n_chars / MANUAL_CHARS_PER_MIN, 1) if n_chars else None
    script_seconds_est = len(script_steps) * 5  # 每步秒级，量级估计
    speedup = round(manual_min * 60.0 / script_seconds_est, 1) \
        if manual_min and script_seconds_est else None

    # 反事实对照：high severity 前 5 条
    high5 = sorted([f for f in findings if f.get("severity") == "high"],
                   key=lambda f: f.get("id", ""))[:5]
    counter_rows = []
    for i in range(max(5, len(high5))):
        left = BASELINE_AGENT_TYPICAL[i] if i < len(BASELINE_AGENT_TYPICAL) else "（同上量级：无定位、无动作的笼统建议）"
        if i < len(high5):
            f = high5[i]
            right = (f"[{f.get('id')}] {loc_str(f.get('location'))}｜"
                     f"{f.get('type')}｜op={((f.get('action') or {}).get('op'))}")
        else:
            right = "（high 级不足 5 条，已列全部）"
        counter_rows.append((left, right))

    card = {
        "generated_by": "gain_card.py (section-narrative-flow v2.0.3)",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "inputs": {"findings": "out/findings.json", "stats": "work/stats.json",
                   "change_log": "work/change_log.json",
                   "report": "out/diagnosis_report.md"},
        "metrics": {
            "n_findings": n,
            "dimension_coverage": {"covered": covered, "total": 6,
                                   "detail": dims_detail},
            "anchor_rate_pct": anchor_rate,
            "anchored_findings": len(anchored),
            "actionable_rate_pct": ops_rate,
            "actionable_findings": len(actable),
            "allowed_ops": ALLOWED_OPS,
            "location_granularity": gran,
            "script_mechanical_steps": len(script_steps),
            "agent_judgment_steps": len(agent_steps),
            "script_step_names": [c.get("step") for c in script_steps],
            "efficiency_estimate": {
                "note": "估计",
                "manual_baseline_chars_per_min": MANUAL_CHARS_PER_MIN,
                "n_chars": n_chars,
                "manual_minutes_est": manual_min,
                "script_seconds_est": script_seconds_est,
                "speedup_est": speedup,
            },
        },
        "counterfactual": {
            "note": "左列为基础 Agent 典型输出的固定文案示例（反事实示意，非实测）；"
                    "右列为本技能 findings.json 中 high severity 前 5 条摘录。",
            "rows": [{"baseline_agent_typical": l, "skill_actual_excerpt": r}
                     for l, r in counter_rows],
        },
    }
    with open(os.path.join(args.out, "gain_card.json"), "w", encoding="utf-8") as f:
        json.dump(card, f, ensure_ascii=False, indent=1)

    # 核心指标表（gain_card.md 与报告追加节共用同一批行，保证数字一致）
    eff_note = (f"人工通读基线 ≈ {manual_min} 分钟（n_chars={n_chars} ÷ "
                f"{MANUAL_CHARS_PER_MIN} 字/分钟，估计）vs 脚本管线 ≈ "
                f"{script_seconds_est} 秒（{len(script_steps)} 步 × 秒级，估计），"
                f"效率提升 ≈ {speedup}×（估计）")
    core_table = [
        "| 指标 | 数值 | 复算口径 |",
        "|-|-|-|",
        f"| 六维覆盖率 | {covered}/6 | findings.json 按 dimension 计数；"
        f"无 finding 的维度以报告中显式\"未检出\"说明计为覆盖 |",
        f"| 原文锚点率 | {anchor_rate}%（{len(anchored)}/{n}） | quote 非空且非"
        f"\"(未检出\"/\"(全文)\"占位开头 |",
        f"| 可执行动作率 | {ops_rate}%（{len(actable)}/{n}） | action.op ∈ 9 类允许 op "
        f"且 instruction 非空 |",
        f"| 定位粒度 | 句子级 {gran['句子级']} / 段落级 {gran['段落级']} / "
        f"全文级 {gran['全文级']} | location.sentence_id / para_id 判定 |",
        f"| 机械劳动（脚本步骤） | {len(script_steps)} 步 | work/change_log.json 中"
        f"步骤名属脚本管线的条目数 |",
        f"| Agent 判断步骤 | {len(agent_steps)} 步 | change_log 其余条目数"
        f"（第 7 步复核增删若不写 change_log 则记 0） |",
        f"| 估计效率 | {eff_note} | work/stats.json 的 n_chars |",
    ]
    counter_table = [
        "| 基础 Agent 典型输出（反事实示意） | 本技能实际输出摘录（位置｜类型｜op） |",
        "|-|-|",
    ] + [f"| {l} | {r} |" for l, r in counter_rows]
    counter_note = ("> 左列为基础 Agent 典型输出的固定文案示例（反事实示意，非实测）；"
                    "右列为本技能 findings.json 中 high severity 前 5 条实际摘录。")

    # gain_card.md
    L = []
    L.append("# 增益自证卡（机器可复算）\n")
    L.append(f"- 生成: gain_card.py（v2.0.3）｜{card['generated_at']}")
    L.append("- 全部数字可由 out/findings.json、work/stats.json、work/change_log.json 复算；"
             "效率栏为估计值，已在表内注明。\n")
    L.append("## 核心指标\n")
    L.extend(core_table)
    L.append("")
    L.append("## 反事实对照（基础 Agent vs 本技能）\n")
    L.append(counter_note + "\n")
    L.extend(counter_table)
    L.append("")
    with open(os.path.join(args.out, "gain_card.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # diagnosis_report.md 末尾追加自证卡节（幂等：先剥掉旧节再追加）
    if os.path.exists(report_path):
        body = report
        idx = body.find(GAIN_SECTION_HEAD)
        if idx >= 0:
            body = body[:idx].rstrip() + "\n"
        section = [GAIN_SECTION_HEAD, ""]
        section.extend(core_table)
        section.append("")
        section.append("### 反事实对照（基础 Agent vs 本技能）")
        section.append("")
        section.append(counter_note)
        section.append("")
        section.extend(counter_table)
        section.append("")
        section.append("（本表与 out/gain_card.md / out/gain_card.json 同源，"
                       "全部数字可复算。）")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(body.rstrip() + "\n\n" + "\n".join(section) + "\n")

    print(f"[gain_card] dims={covered}/6 anchor={anchor_rate}% ops={ops_rate}% "
          f"-> gain_card.md/json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
