# 最小调用示例（示例，非正式案例结果）

## 输入

- `/input/case.json`：`{"case_id":"demo-sty-001","output_contract":{"result":"主交付物"}}`
- `/input/task.md`：将 manuscript.md 英译中。
- `/input/manuscript.md`（合成）：

```markdown
## Abstract
We synthesized the material. It was tested under humid conditions.
```

## 调用

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
# Agent 翻译 → translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/style_engine.py audit --work $W
# Agent 修订 → 重跑上两步
python3 $S/report_builder.py --work $W --out $O --focus style --skill "academic-style-control v1.0.3"
python3 $S/assemble_result.py --work $W --out $O --skill "academic-style-control v1.0.3" --status success
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 示意输出（示例）

初译：`"我们对材料进行了合成。它在潮湿条件下被进行了测试。"`
机检：STY-001 动词名词化（进行了合成）、STY-002 被动滥用+动词名词化（被进行了测试）。
修订：`"我们合成了该材料，并在潮湿条件下进行了测试。"`——复核：“进行了测试”
与“测试了”等价，统一为“测试了”更佳；复检 issues=0。
