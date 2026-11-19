# USAGE｜完整调用步骤（v1.0.4 引用覆盖审计）

执行序列与 v1.0.0 相同，差异：Phase 3 登记 ref_classification.jsonl 并精细维护
claim_bindings.jsonl；Phase 4 首跑 coverage_audit.py。

```bash
S=/skills/weekly-skill/scripts
# Phase 0-1 同共享管线
# Agent 写作：ref_classification.jsonl → evidence_map.json → draft_intro/draft_rl
#   → claim_bindings.jsonl（逐句、选对 claim_type）
python3 $S/coverage_audit.py --work /app/work --out /app/output
python3 $S/build_deliverables.py --work /app/work --out /app/output
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json --skill "citation-coverage-audit v1.0.4" --status success
python3 $S/validate_output.py --out /app/output --expect-status success
python3 $S/render_previews.py --out /app/output
```

## 输出

coverage_report.md（分类问题/裸论断/未覆盖关键工作/近期覆盖/元数据缺失）、introduction.md、
related_work.md、references.md、evidence_map.json、build_report.json、version_report.json、
result.json（含 manual_confirmations）、preview.html。

## 自查要点

- version_report.json：classification_issues 空；naked_claims 空；
  uncovered_key_works 空或已确认；recent.ratio ≥ 1/3。
- validate_output：正文引用与文献表双向一致（stray/unused 均为空）。

## 失败处理

裸论断 → 补 binding 或删行；漏引关键工作 → 补转述或确认不引；分类缺口 → 补 rationale；
脚本幂等可重跑。
