# 最小调用示例（示意输出标注为示例，非正式案例结果）

## 输入

`/input/case.json`：`{"case_id":"demo-rf","output_contract":{"polished_text":"x","change_log":"y","style_report":"z"}}`
`/input/task.md`：把这段基金本子润色为基金申请书语域，保持数值与"有望"类限定。
`/input/proposal.md`：

```markdown
我们做了一个非常高通量的筛选方法，非常非常厉害。 moreover，通过机器学习我们有望把发现周期缩短50%。由于效率高，所以它会改变材料研发。
```

## 调用

```bash
python3 /skills/weekly-skill/scripts/segment_util.py --input-dir /input --work-dir /app/work --output-dir /app/output
python3 /skills/weekly-skill/scripts/style_metrics.py profile --segments /app/work/source_segments.json --register "基金申请书" --out /app/work
# Agent 逐句换装写 chunks → assemble → compare 验证 → 处置未达标 → validate
python3 /skills/weekly-skill/scripts/assemble.py --work-dir /app/work --output-dir /app/output --bilingual
python3 /skills/weekly-skill/scripts/style_metrics.py compare --source /app/work/source_segments.json --polished /app/work/polished_segments.json --out /app/work
python3 /skills/weekly-skill/scripts/validate_output.py --work-dir /app/work --output-dir /app/output
```

## 示意 style_report.md（示例）

| 指标 | 润色前 | 润色后 | 目标区间 |
|---|---|---|---|
| 平均句长 | 24.0 | 27.5 | 25–45 |
| 限定词密度 | 0.33 | 0.33 | 0.2–0.8 |
| 宣传/绝对化词 | 2 | 0 | ≤0 |
| 口语词 | 3 | 0 | ≤0 |

全部指标达标 ✓（"有望""缩短50%"限定与数值守恒；moreover 位置修正；由于…所以…冗余删除）
