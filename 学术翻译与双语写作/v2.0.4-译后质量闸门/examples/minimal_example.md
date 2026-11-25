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

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
python3 $S/number_engine.py ledger --work $W
# Agent 翻译 → translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/qa_gate.py --work $W
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "translation-qa-gate v2.0.4"
python3 $S/assemble_result.py --work $W --out $O --skill "translation-qa-gate v2.0.4" --status success
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

## 质量闸门示意（示例）

`qa_report.json`（节选）：

```json
{"summary":{"total":3,"by_severity":{"高":1,"中":2,"低":0}},
 "fix_list":[
  {"rank":1,"severity":"高","dimension":"语义边界","type":"引用标记缺失",
   "seg_id":"P002-s1","instruction":"恢复引用标记 [1] 于对应论断句末（原位原格式）"},
  {"rank":2,"severity":"中","dimension":"事实与数字","type":"疑似四舍五入/笔误",
   "seg_id":"P001-s2","instruction":"恢复源数字「23.4%」原值与单位"}]}
```
