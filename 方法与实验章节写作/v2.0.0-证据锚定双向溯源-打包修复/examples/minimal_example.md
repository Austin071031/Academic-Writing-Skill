# 最小调用示例（合成材料，标注为示例，非正式案例结果）

## 输入（合成）

`/input/case.json`：

```json
{"case_id": "demo-01", "task": "依据材料撰写方法与实验章节",
 "output_contract": {"chapter_path": "str", "verification": "object"}}
```

材料：`paper.pdf`（方法段写明 learning rate 3e-4、batch size 32、10 epochs、seed 42）、
`config.yaml`、`train.log`、`train.py`、`data_card.md`（均合成）。

## 调用

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 /skills/weekly-skill/scripts/extract_evidence.py --work /app/work
# Agent 依据 references/ 写 work/sections/*.md 与台账文件（见 docs/USAGE.md Phase 3）
python3 /skills/weekly-skill/scripts/build_deliverables.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/audit_provenance.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work --expect-status success
```

## 示意输出（示例，非真实案例结果）

`methods_chapter.md` 片段：

> ## 3 参数与来源
> 超参数取自配置文件：learning_rate 3e-4〔E0005〕、batch_size 32〔E0006〕；
> 日志确认实际运行 learning_rate 0.0003〔E0013〕，与配置值一致。

`audit_report.json`：`{"forward_leaks": [], "backward_unused": [], "verdict": "pass"}`

`result.json` 关键字段：`status="success"`，`outputs.methods_chapter="methods_chapter.md"`，
`evidence_map` 14 条，`manual_confirmations` 1 条（基线数值缺口）。
