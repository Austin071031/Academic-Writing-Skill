# 最小调用示例（示例，非正式案例结果）

## 输入

- `/input/case.json`：`{"case_id":"demo-aln-001","output_contract":{"result":"主交付物"}}`
- `/input/task.md`：将 manuscript.md 英译中，交付双语对照。
- `/input/manuscript.md`（合成）：

```markdown
## Abstract
We report a new catalyst. It shows 95% selectivity.
Figure 1. Structure of the catalyst.
```

## 调用

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
python3 $S/align_engine.py plan --work $W
# Agent 翻译 → translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/align_engine.py audit --work $W --out $O
python3 $S/report_builder.py --work $W --out $O --focus alignment --skill "bilingual-alignment-guard v1.0.2"
python3 $S/assemble_result.py --work $W --out $O --skill "bilingual-alignment-guard v1.0.2" --status success
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 示意输出（示例）

`bilingual.md`（节选）：

```markdown
## 〔SEC2〕 Abstract
## 〔SEC2·译〕 摘要

〔P001·原文〕 We report a new catalyst. It shows 95% selectivity.

〔P001·译文〕 我们报道了一种新催化剂。其选择性为95%。

〔P002·caption·原文〕 Figure 1. Structure of the catalyst.

〔P002·caption·译文〕 图1. 催化剂结构。
```

`alignment.json` summary：`{"aligned":3,"missing":0,"suspect":0,"kept_original":0}`。
