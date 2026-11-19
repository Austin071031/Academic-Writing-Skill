# 最小调用示例（示例，非正式案例结果）

## 输入
- task.md：请将论文材料改写为面向公众的科普文章（≤800 字）并附 200 字新闻简报，两个产物术语统一。
- source_paper.md：含"硫化物固态电解质（SSE）""固体电解质""NCM811""LiNbO3""原子层沉积（ALD）"的论文节选（合成）。

## 调用
```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 /skills/weekly-skill/scripts/parse_source.py /input/source_paper.md --work /app/work
python3 /skills/weekly-skill/scripts/terminology_engine.py candidates --source /app/work/source.json --work /app/work
# Agent 审定 term_table_draft.json → 另存 work/term_table.json，再撰写 work/rewrite_draft.md 与 work/briefing.md
python3 /skills/weekly-skill/scripts/align_rewrite.py --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --work /app/work
python3 /skills/weekly-skill/scripts/terminology_engine.py audit --table /app/work/term_table.json --rewrite /app/work/rewrite_draft.md --more /app/work/briefing.md --work /app/work
```

## 示意输出（示例）
- term_table_draft.json：6 条术语；T001 canonical=硫化物固态电解质，variants=[SSE, 固体电解质, 固态电解质, …]，first_expand=true。
- terminology_audit.json：verdict=PASS，0 critical / 0 warn（改写稿与简报统一用 canonical，SSE/ALD 均已首次展开）。
- rewrite.md：完整科普稿（标题+3 段），术语全表锁定；term_table.md：人读术语表 5 条。
