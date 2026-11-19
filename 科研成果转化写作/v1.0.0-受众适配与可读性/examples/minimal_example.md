# 最小调用示例（示例，非正式案例结果）

## 输入
- task.md：请将给定论文材料改写为面向公众的科普文章，篇幅控制在 800 字以内。
- source_paper.md：一段含 ALD/XPS 缩写与 85.3%、62.1% 等数据的论文节选（合成）。

## 调用
```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --work /app/work
python3 /skills/weekly-skill/scripts/parse_source.py /input/source_paper.md --work /app/work
python3 /skills/weekly-skill/scripts/audience_engine.py profile --inspection /app/work/inspection.json --source /app/work/source.json --work /app/work
# Agent 撰写 /app/work/rewrite_draft.md
python3 /skills/weekly-skill/scripts/align_rewrite.py --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --work /app/work
python3 /skills/weekly-skill/scripts/audience_engine.py check --rewrite /app/work/rewrite_draft.md --work /app/work
```

## 示意输出（示例）
- audience_profile.json：受众=公众/科普读者，术语计划 4 条，句长目标 ≤45 字。
- readability_report.json：verdict=PASS，平均句长 27.6 字，篇幅 200/800 字。
- rewrite.md：完整科普稿（标题+3 段），数据 85.3%/62.1%/5 nm 与源文一致。
