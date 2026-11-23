# 最小调用示例（合成示例，非正式测试案例）

输入：task.md（"撰写引言，GB/T 7714 引用"）、paper.pdf（含参考文献节）、draft.md（底稿带 [1]-[5] 引用）。

```bash
bash /skills/weekly-skill/scripts/run.sh pre
# → library.md：解析出 12 条文献（R001-R012，3 条标⚠缺DOI）
# Agent 写引言，引用 [1][2][4]；文献表收录被引条目
bash /skills/weekly-skill/scripts/run.sh post
# → citation_audit.md：FAIL——[3] 超出文献表范围（悬空）；[5] 条目未被引用（装饰性）
# Agent 修正后重跑 post → PASS；绑定表逐条复核语义后交付
```
