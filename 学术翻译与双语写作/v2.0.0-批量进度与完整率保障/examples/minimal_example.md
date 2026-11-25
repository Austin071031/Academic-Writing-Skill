# 最小调用示例（示例，非正式案例结果）

## 输入

- `/input/case.json`：`{"case_id":"demo-num-001","output_contract":{"result":"主交付物"}}`
- `/input/task.md`：将 manuscript.md 英译中，交付纯译文与双语对照。
- `/input/manuscript.md`（合成）：

```markdown
## Results
The champion cell reached 23.4% at 1.18 V after 1000 h. Over 1.2 million data points
were collected between 2015 and 2024.
```

## 调用

> v2.0.0 增量：`number_engine.py ledger` 之后增加 `batch_planner.py plan`（生成
> work/batches/ 批文件与 progress.json），Agent 按批翻译并以
> `batch_planner.py status --used-requests N` 追踪进度与预算告警。

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
python3 $S/number_engine.py ledger --work $W
# Agent 翻译 → translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/number_engine.py audit --work $W
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "translation-completion-guard v2.0.0"
python3 $S/assemble_result.py --work $W --out $O --skill "translation-completion-guard v2.0.0" --status success
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 示意输出（示例）

`work/translations.jsonl`：

```jsonl
{"seg_id":"SEC1-h","translation":"结果"}
{"seg_id":"P001-s1","translation":"冠军电池在1000 h后于1.18 V下达到23.4%。"}
{"seg_id":"P001-s2","translation":"2015年至2024年间共采集超过120万个数据点。"}
```

`number_audit.json` summary：`{"source_numbers":7,"matched_numbers":7,"fidelity":1.0,"issues":0}`
（1.2 million ↔ 120万 归一等值通过）。
