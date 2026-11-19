# USAGE｜完整调用步骤（v1.0.3 贡献证据对齐）

执行序列与 v1.0.0 相同，差异：Phase 3 登记 contributions.json；Phase 4 首跑 contribution_align.py。

```bash
S=/skills/weekly-skill/scripts
# Phase 0-1 同共享管线
# Agent 写作：evidence_map.json → contributions.json → draft_intro.md（贡献段逐条对应）
#   → draft_rl.md → claim_bindings.jsonl
python3 $S/contribution_align.py --work /app/work --out /app/output
python3 $S/build_deliverables.py --work /app/work --out /app/output
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json --skill "contribution-evidence-alignment v1.0.3" --status success
python3 $S/validate_output.py --out /app/output --expect-status success
python3 $S/render_previews.py --out /app/output
```

## 输出

contributions_check.md（贡献-证据对照表）、introduction.md、related_work.md、references.md、
evidence_map.json、build_report.json、version_report.json、result.json（含 manual_confirmations）、preview.html。

## 自查要点

- version_report.json：每条贡献 issues 空；scope_flags 有登记即进入 manual_confirmations；verdict=pass。
- 对照表逐行：类型与证据类型匹配；数字列在证据段落中出现。
- build_report.json：锚点全解析、绑定 ≥90%、四要素全 true。

## 失败处理

数字不可回溯 → 改正数字或更换证据位置；证据位置找不到 → 核对 pid/图表编号；
overclaim_risk → 改写或人工确认；脚本幂等可重跑。
