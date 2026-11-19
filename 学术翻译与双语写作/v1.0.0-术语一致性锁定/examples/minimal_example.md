# 最小调用示例（示例，非正式案例结果）

> 输入、输出均为合成示意，用于说明接口与完整流程，不冒充正式案例结果。

## 输入

- `/input/case.json`：`{"case_id":"demo-001","output_contract":{"result":"主交付物"}}`
- `/input/task.md`：将 manuscript.md 英译中，交付纯译文与双语对照。
- `/input/manuscript.md`（合成）：

```markdown
## Abstract
Solid-state batteries (SSBs) may improve safety. The ionic conductivity reached 3.2 mS/cm.
```

## 调用

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
python3 $S/term_engine.py seed --work $W
# Agent：审定 glossary.json（SSBs→固态电池；ionic conductivity→离子电导率）
# Agent：写 translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/term_engine.py audit --work $W
python3 $S/report_builder.py --work $W --out $O --focus terminology --skill "translation-terminology-lock v1.0.0"
python3 $S/assemble_result.py --work $W --out $O --skill "translation-terminology-lock v1.0.0" --status success
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 示意输出（示例）

`work/translations.jsonl`：

```jsonl
{"seg_id":"SEC1-h","translation":"摘要"}
{"seg_id":"P001-s1","translation":"固态电池（SSBs）有望提升安全性。"}
{"seg_id":"P001-s2","translation":"离子电导率达到3.2 mS/cm。"}
```

`term_audit.json` summary：`{"terms_locked":2,"violations":0}`；
`result.json`：`status=success`，outputs 含 translation_full / bilingual / glossary / term_audit。
