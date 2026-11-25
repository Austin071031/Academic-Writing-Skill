# 最小调用示例（合成材料，标注为示例，非正式案例结果）

## 输入（合成）

同前：`case.json`（demo-03）+ 合成 paper.pdf / config.yaml / train.log / train.py / data_card.md。

## 关键差异：复现清单

`work/repro_checklist.json`（示意）：

```json
{"code_version": "git tag v1.2.0", "environment": {"os": "Ubuntu 22.04", "python": "3.11"},
 "hardware": "1×A100 80GB", "data_acquisition": {"path": "data_card.md"},
 "commands": ["python train.py --config config.yaml"], "seeds": ["42"], "est_cost": "约 2 GPU·时"}
```

## 调用与示意输出

Phase 4 首步：

```bash
python3 /skills/weekly-skill/scripts/repro_gate.py --work /app/work --out /app/output
```

示意输出（示例）：`repro_report.json` 缺项为空、`commands_not_in_chapter` 为空时
`verdict=pass`。若删掉清单中的 seeds，`missing=["seeds"]` 且 status 必须降级 partial
——闸门不允许带着缺口宣称可复现（示意行为，非正式案例结果）。
