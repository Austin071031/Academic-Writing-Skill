# 最小调用示例（合成示例，非正式测试案例）

输入：task.md（"按数据核对并修订底稿"）、draft.md（底稿）、data.csv（数据）。

```bash
bash /skills/weekly-skill/scripts/run.sh pre
# → task_profile.md：mode=rewrite，底稿 draft.md 已快照（14 段）
# Agent 修订并逐条写 change_log.md（[数字] P005 "61%"→"61.2%" — M01#row2）
bash /skills/weekly-skill/scripts/run.sh post
# → audit_report.md：摘要"92.3%"正文有 ✅；图 2 缺图注 ❌ FAIL → 补图注重跑
# → diff_review.md：删除 2 段/新增 1 段逐段列出；change_log 覆盖检查 PASS
```
