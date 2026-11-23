# 最小调用示例（合成示例，非正式测试案例）

输入：case.json（output_contract 6 字段）、task.md（"依据数据写结果节，约 800 字，GB/T 7714"）、results.csv、notes.md。

```bash
bash /skills/weekly-skill/scripts/run.sh pre
# → brief.json + facts_ledger.md（F0001… 每条数字带 M01#row3 锚点）
# Agent 写 sections/01-results.md：25 °C 处理组产率 92.3% ± 1.8%（F0004）…
cat /app/work/sections/*.md > /app/output/manuscript.md
bash /skills/weekly-skill/scripts/run.sh post
# → number_trace.md：checked 20 / unmatched 0；verdict=PASS；result.json status=success
```

异常演示（示例）：在稿件写入台账没有的 "97.5%" → post 后 number_trace.md 列为 ❌、verdict=FAIL、status=partial。
