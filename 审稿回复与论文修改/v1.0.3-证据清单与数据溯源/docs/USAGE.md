# 使用说明（USAGE）

## 平台评测模式（主要用途）

平台把本目录安装到 `/skills/weekly-skill`，对固定案例运行 Agent。Agent 读到任务后按 SKILL.md 第 3 节步骤 0–8 执行即可；输入在 `/input/`，输出写 `/app/output/`。

## 独立复用模式

```bash
export SKILL=/path/to/v1.0.3-证据清单与数据溯源
mkdir -p /tmp/work /tmp/output
python3 $SKILL/scripts/init_result.py --case case.json --out /tmp/output
python3 $SKILL/scripts/inspect_case.py --case case.json --task task.md --input-dir . --work /tmp/work
python3 $SKILL/scripts/parse_manuscript.py --work /tmp/work --file path/to/manuscript-baseline.md
python3 $SKILL/scripts/parse_comments.py --work /tmp/work --file path/to/reviewer-comments.md
# → Agent 复核 comments.json（重点：needs_evidence 与 action_kind）
# → 撰写 dispositions.json（共享证据引用同一 EV 编号）与 edit_plan.json
python3 $SKILL/scripts/evidence_engine.py --work /tmp/work --out /tmp/output --stage demand
# → Agent 终判 evidence_checklist.json 的 status/note 后重跑一次 demand
python3 $SKILL/scripts/revision_engine.py --work /tmp/work --out /tmp/output
# → 撰写 response_letter.md / edit_locations.md 等；可再跑 demand 校准状态
python3 $SKILL/scripts/evidence_engine.py --work /tmp/work --out /tmp/output --stage provenance
# exit=2 → 逐条处置未核实数字（确认留档 或 改【待补】后重跑）
python3 $SKILL/scripts/verify_revision.py --work /tmp/work --out /tmp/output
python3 $SKILL/scripts/assemble_result.py --work /tmp/work --out /tmp/output \
  --case case.json --skill "revision-evidence-provenance v1.0.3" --status success
python3 $SKILL/scripts/validate_output.py --out /tmp/output --work /tmp/work
```

## evidence_engine 两阶段速查

| 阶段 | 何时跑 | 读什么 | 写什么 | exit |
|-|-|-|-|-|
| demand | 步骤 4 后（步骤 5 后可再跑校准） | comments.json + dispositions.json + edit_plan.json（+ edit_report.json 若有） | work/evidence_checklist.json、output/evidence_checklist.md | 0 |
| provenance | 步骤 7（回复信定稿后、交付前） | 回复信 + edit_plan/edit_report + structure.json + comments.json + evidence_checklist.json | output/provenance_report.md、work/provenance.json、work/evidence_map.json、work/manual_confirmations.json（合并） | 0=全部溯源通过；2=有未核实数字（告警） |

## 输入约定

- case.json：`case_id` + `output_contract`（字段列表，原样回填）；
- 稿件与意见文件名不限，inspect_case 按名称与内容双重嗅探；判错时用 `--file` 显式指定；
- 数字溯源依赖 structure.json 的 `source_file` 指向可读的基线原文；基线不可读时全部数字无法溯源，provenance 会告警——此时应修复读取路径而非强行交付。

## 失败处理

任何脚本 FATAL → 读 stderr 原因；材料缺失 → result.json status=failed 并说明；锚点失败 → 修 quote 重跑；provenance exit=2 → 处置 manual_confirmations 中的未核实数字；Agent 终判被脚本覆盖 → 检查是否直接改了 /app/output 的 md 而非 work/evidence_checklist.json（重跑以 work 下 JSON 为准）。详见 SKILL.md 第 4 节异常表。
