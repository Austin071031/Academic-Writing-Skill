# 最小调用示例（示例，非正式案例结果）

## 输入
- task.md：请将给定论文摘要材料改写为一则新闻通稿。
- source_paper.md：一段含 85.3%、62.1%、500 次循环等数据的论文摘要节选（合成）。

## 调用
```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --work /app/work
python3 /skills/weekly-skill/scripts/parse_source.py /input/source_paper.md --work /app/work
python3 /skills/weekly-skill/scripts/genre_engine.py map --inspection /app/work/inspection.json --source /app/work/source.json --work /app/work
# Agent 按 genre_mapping.json 的要素模板撰写 /app/work/rewrite_draft.md，
# 并逐段写 /app/work/change_reasons.jsonl
python3 /skills/weekly-skill/scripts/align_rewrite.py --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --work /app/work
python3 /skills/weekly-skill/scripts/genre_engine.py ledger --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --reasons /app/work/change_reasons.jsonl --work /app/work
```

## 示意输出（示例）
- genre_mapping.json：genre=新闻通稿；7 个要素中 6 个已映射源文段落；
  「联系方式占位」缺失 → 标注「源文未提供」并记 manual_confirmations。
- change_reasons.jsonl：6 条改写段落理由 + 1 条删除理由（删去重复背景句）。
- change_ledger.json：verdict=PASS；源文 6 段全部有去向（5 覆盖 + 1 删除有理由），
  改写 7 段均有来源或已声明「新增-过渡」。
- traceability_report.md：两张逐段对照表，含每段动作、理由与涉及事实数。
- 反例对照：删除含数据的源文段落却不写理由 → critical，ledger exit=2。
