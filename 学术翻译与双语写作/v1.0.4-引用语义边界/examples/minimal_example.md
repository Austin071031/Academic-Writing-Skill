# 最小调用示例（示例，非正式案例结果）

## 输入

- `/input/case.json`：`{"case_id":"demo-bnd-001","output_contract":{"result":"主交付物"}}`
- `/input/task.md`：将 manuscript.md 英译中。
- `/input/manuscript.md`（合成）：

```markdown
## Results
The coating did not degrade under humid conditions [3]. This suggests the barrier may
be effective (Lee et al., 2022).
```

## 调用

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
python3 $S/boundary_engine.py index --work $W
# Agent 翻译 → translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/boundary_engine.py audit --work $W
python3 $S/report_builder.py --work $W --out $O --focus boundary --skill "citation-semantic-boundary v1.0.4"
python3 $S/assemble_result.py --work $W --out $O --skill "citation-semantic-boundary v1.0.4" --status success
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 示意输出（示例）

合规译文：

```jsonl
{"seg_id":"P001-s1","translation":"该涂层在潮湿条件下未发生降解[3]。"}
{"seg_id":"P001-s2","translation":"这表明该阻挡层可能有效（Lee et al., 2022）。"}
```

`boundary_audit.json` summary：`{"citations_total":2,"citations_preserved":2,
"citation_fidelity":1.0,"issues":0}`；否定（未）、表明类（表明）、可能性（可能）
均等强保留。
