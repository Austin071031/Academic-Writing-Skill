# 最小调用示例（示意输出均为示例，非正式案例结果）

## 输入

`/input/case.json`：
```json
{"case_id": "demo-000", "output_contract": {"polished_text": "润色后全文", "change_log": "逐句修改清单"}}
```

`/input/task.md`：请将 manuscript.md 按期刊论文语域润色，保持数值与引用不变，交付改后全文与逐句修改说明。

`/input/manuscript.md`：
```markdown
## 摘要
我们提出了一种新的方法，可以显著提高预测精度。实验结果显示，误差降低了约15%[1]。结果表明，该方法有望推广应用。
```

## 调用

```bash
SKILL=/skills/weekly-skill   # 本地调试时为克隆目录
bash $SKILL/scripts/run_pipeline.sh /input /app/work /app/output
python3 $SKILL/scripts/terminology.py build --segments /app/work/source_segments.json --out /app/work
# Agent 逐句决策写入 /app/work/polish_chunks/chunk_001.jsonl（每句一行 JSON）
python3 $SKILL/scripts/assemble.py --work-dir /app/work --output-dir /app/output --bilingual
python3 $SKILL/scripts/terminology.py check --segments /app/work/polished_segments.json --table /app/work/term_table.csv --out /app/work
python3 $SKILL/scripts/guard_check.py --source /app/work/source_segments.json --chunks /app/work/polish_chunks --out /app/work
# 对 critical 逐条修正或在 /app/work/resolutions.jsonl 记录处置，然后：
python3 $SKILL/scripts/assemble.py --work-dir /app/work --output-dir /app/output --bilingual
python3 $SKILL/scripts/render_previews.py --output-dir /app/output
python3 $SKILL/scripts/validate_output.py --work-dir /app/work --output-dir /app/output
```

## chunk_001.jsonl（示例）

```jsonl
{"id":"manuscript-B2-P1-S1","original":"我们提出了一种新的方法，可以显著提高预测精度。","polished":"本文提出了一种新方法，可显著提高预测精度。","decision":"modify","types":["register"],"reason":"去人称主语，书面语更紧凑"}
{"id":"manuscript-B2-P1-S2","original":"实验结果显示，误差降低了约15%[1]。","polished":"实验结果显示，误差降低了约15%[1]。","decision":"keep","types":[],"reason":"无语病；数值、单位与引用编号守恒"}
{"id":"manuscript-B2-P1-S3","original":"结果表明，该方法有望推广应用。","polished":"结果表明，该方法有望推广应用。","decision":"keep","types":[],"reason":"表述规范，限定强度恰当"}
```

## 示意输出（标注：以下为示例，非正式案例结果）

`/app/output/change_log.md`：
```markdown
# 逐句修改清单（change log）
句子总数 3；修改 1；保留 2；未记录 0。
## 逐句对照（仅列出 decision=modify 的句子）
| ID | 原文 | 改文 | 修改类型 | 理由 |
|---|---|---|---|---|
| manuscript-B2-P1-S1 | 我们提出了一种新的方法，可以显著提高预测精度。 | 本文提出了一种新方法，可显著提高预测精度。 | register(语域语气) | 去人称主语，书面语更紧凑 |
```

`/app/output/result.json`（节选）：
```json
{"case_id": "demo-000", "status": "complete",
 "output_contract": {"polished_text": {"delivered": "polished_full.md", ...},
                     "change_log": {"delivered": "change_log.md", ...}},
 "change_records": {"summary": {"sentences_total": 3, "modified": 1, "kept": 2, "unlogged": 0}},
 "fact_preservation": {"critical_unresolved": 0, "coverage_ratio": 1.0},
 "uncertainty": [], "manual_review_required": []}
```
