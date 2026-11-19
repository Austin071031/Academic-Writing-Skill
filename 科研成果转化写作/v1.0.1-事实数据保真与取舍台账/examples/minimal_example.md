# 最小调用示例（示例，非正式案例结果）

## 输入
- task.md：请将给定论文材料改写为面向公众的科普文章，篇幅控制在 800 字以内，保留关键数据与结论。
- source_paper.md：硫化物固态电解质论文片段（合成），含 5 nm、85.3%、62.1%、320 Ω→85 Ω（降 73.4%）、图2、表1、2023 年 78% 等事实。

## 调用
```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 /skills/weekly-skill/scripts/parse_source.py /input/source_paper.md --work /app/work
# Agent 先写 /app/work/retention_decisions.jsonl（5 段逐段决定）
# Agent 再写 /app/work/rewrite_draft.md（完整科普稿，数据与源文一致）
python3 /skills/weekly-skill/scripts/align_rewrite.py --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --work /app/work
python3 /skills/weekly-skill/scripts/fidelity_engine.py check --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --work /app/work
python3 /skills/weekly-skill/scripts/fidelity_engine.py ledger --decisions /app/work/retention_decisions.jsonl --work /app/work
```

## 示意输出（示例，非正式案例结果）
- fidelity_report.json：verdict=PASS；verbatim 7，derived 0，missing 0，altered 0，unverified 0；遮蔽 token 5（0.5C、LiNi0.8 等）。
- retention_ledger.json：决定 5 条，覆盖关键段落 3 个，删除 0，errors=0。
- rewrite.md：完整科普稿（标题+3 段），85.3%/62.1%/73.4%/5 纳米/320 欧姆/85 欧姆/图2/表1 与源文一致。

## 反例（同样示例性质）
- 把 85.3% 改成 89%：check 判 FAIL——altered 1（critical）+ unverified 1（`89%` 源外）。
- 新增"能量密度提升 40%"：check 判 FAIL——unverified 1（critical）。
- 删除含 85.3% 的段落且 retention_decisions 无理由：ledger 判 FAIL——missing_decision/unreasoned_action（exit=2）。
