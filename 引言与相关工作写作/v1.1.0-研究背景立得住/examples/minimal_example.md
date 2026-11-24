# 最小调用示例（合成材料，非正式案例结果）

> 本示例使用合成材料演示接口与完整流程；输出为示意，不冒充任何正式案例结果。

## 输入（合成）

case.json（output_contract 含 introduction/related_work/references/evidence_map/status）；
task.md 要求"起草引言与相关工作，GB/T 7714，中文"；
材料：manuscript_draft.md（底稿）、references.bib（3 条）、reading_notes.md（2 段）。

## 调用

```bash
python3 scripts/init_result.py --case /input/case.json --out /app/output
python3 scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 scripts/parse_manuscript.py /input/manuscript_draft.md --work /app/work
python3 scripts/parse_library.py /input/references.bib --work /app/work
python3 scripts/parse_notes.py /input/reading_notes.md --work /app/work
python3 scripts/extract_facts.py --work /app/work
# Agent 写作阶段：写 work/evidence_map.json（含 cite 字段）、draft_intro.md、draft_rl.md
# （v1.1.0 起引用绑定由引擎从锚点自动派生，不再写 claim_bindings.jsonl）
python3 scripts/anti_fluff.py --work /app/work --out /app/output --patterns references/anti_fluff_patterns.txt
python3 scripts/build_deliverables.py --work /app/work --out /app/output
python3 scripts/assemble_result.py --work /app/work --out /app/output --case /input/case.json --skill "intro-background-grounding v1.0.0" --status success
python3 scripts/validate_output.py --out /app/output --expect-status success
python3 scripts/render_previews.py --out /app/output
```

## 示意输出（节选）

build_report.json：

```json
{"anchors": {"total": 9, "resolved": 9, "missing": []},
 "bindings": {"total": 7, "matched": 7, "missed": [], "auto_derived": 7},
 "sections": {"intro_background": true, "intro_gap": true, "intro_contributions": true, "rl_groups": 2},
 "reference_order": ["1=R001", "2=R002"]}
```

introduction.md（示意）：

```markdown
# 引言
## 研究背景与问题
……未改性样品暴露 1 小时后电导率下降约 40%[1]。……保护层开裂问题仍未解决[2]。
## 研究空白
……
## 本文贡献
……（证据见 P003、图2）
```

result.json 含 case_id、status=success、outputs 清单、evidence_map、exceptions=[]、
output_contract_fields 全部回填。
