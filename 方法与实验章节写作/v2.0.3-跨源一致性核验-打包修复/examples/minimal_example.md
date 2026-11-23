# 最小调用示例（合成材料，标注为示例，非正式案例结果）

## 输入（合成）

同前：`case.json`（demo-04）+ 合成材料。本例特意让三处 learning_rate 不同：
config.yaml 3e-4、train.log 0.0003（等价）、train.py 默认 1e-3（被覆盖）。

## 关键差异：机检 + 裁决

```bash
python3 /skills/weekly-skill/scripts/cross_source_check.py --phase detect --work /app/work --out /app/output
# -> work/conflicts.jsonl 记 1 条候选（learning_rate 跨三源多值，3e-4 与 0.0003 归一同组）
```

`work/conflict_resolutions.json`（示意）：

```json
[{"name": "learning_rate", "chosen_value": "3e-4",
  "rule": "日志实际运行 > 配置 > 代码默认", "rationale": "E0013 运行值 0.0003=3e-4；E0015 默认 1e-3 被配置覆盖",
  "eids": ["E0005", "E0013", "E0015"]}]
```

```bash
python3 /skills/weekly-skill/scripts/cross_source_check.py --phase verify --work /app/work --out /app/output
# -> consistency_report.json: conflicts_total=1 resolved=1 verdict=pass
```

示意行为（示例，非正式案例结果）：删除该裁决后 verify 报 unresolved=1、verdict=fail，
status 必须降级——裁决闭环有效。
