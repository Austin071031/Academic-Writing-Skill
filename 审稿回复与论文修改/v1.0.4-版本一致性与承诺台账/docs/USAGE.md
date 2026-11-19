# 使用说明（USAGE）

## 平台评测模式（主要用途）

平台把本目录安装到 `/skills/weekly-skill`，对固定案例运行 Agent。Agent 读到任务后按 SKILL.md 第 3 节步骤 0–8 执行即可；输入在 `/input/`，输出写 `/app/output/`。多轮返修案例的轮次由 case.json 的 `constraints.round` / `revision_round` 给出，consistency_engine 自动读取，无需手工指定。

## 独立复用模式

```bash
export SKILL=/path/to/v1.0.4-版本一致性与承诺台账
mkdir -p /tmp/work /tmp/output
python3 $SKILL/scripts/init_result.py --case case.json --out /tmp/output
python3 $SKILL/scripts/inspect_case.py --case case.json --task task.md --input-dir . --work /tmp/work
python3 $SKILL/scripts/parse_manuscript.py --work /tmp/work --file path/to/manuscript-baseline.md
python3 $SKILL/scripts/parse_comments.py --work /tmp/work --file path/to/reviewer-comments.md
# → 人工/Agent 复核 comments.json，撰写 dispositions.json 与 edit_plan.json
python3 $SKILL/scripts/revision_engine.py --work /tmp/work --out /tmp/output
# → 撰写 response_letter.md / edit_locations.md / evidence_checklist.md 等
python3 $SKILL/scripts/consistency_engine.py --work /tmp/work --out /tmp/output \
    --case case.json --input-dir .
python3 $SKILL/scripts/verify_revision.py --work /tmp/work --out /tmp/output
python3 $SKILL/scripts/assemble_result.py --work /tmp/work --out /tmp/output \
    --case case.json --skill "revision-version-consistency v1.0.4" --status success
python3 $SKILL/scripts/validate_output.py --out /tmp/output --work /tmp/work
```

## consistency_engine 参数

| 参数 | 缺省 | 说明 |
|-|-|-|
| `--work` | /app/work | 中间 JSON 目录（需 structure/edit_report/dispositions） |
| `--out` | /app/output | 产物目录（需 revised_manuscript.md；response_letter.md 可选） |
| `--baseline` | structure.json 的 source_file | 基线稿件路径，可显式覆盖 |
| `--case` | /input/case.json | 读取轮次（constraints.round / revision_round，缺省第 1 轮） |
| `--input-dir` | /input | 历史回复文件嗅探目录（递归，含 materials/） |

退出码：0 = 无 FAIL（WARN 需人工确认）；1 = 存在 FAIL；2 = 致命输入缺失。

产物：`consistency_report.md`（对账报告，含承诺台账节）、`revision_ledger.json`（承诺台账）、`work/consistency.json`（机器可读结果）。

## 输入约定

- case.json：`case_id` + `output_contract`（原样回填）+ 可选轮次字段；
- 稿件与意见文件名不限，inspect_case 按名称与内容双重嗅探，判错时用 `--file` 显式指定；
- 上一轮回复信命名含 response/reply/回复/rebuttal/round/r1 即可被自动嗅探（约定见 references/consistency_rules.md 第 5 节）。

## 失败处理

- consistency exit=1 → 读 consistency_report.md 第 4 节 FAIL 汇总逐项修复：幽灵 E# 改引用或删除；"声称已改但无实际差异"检查编辑是否真实生效；"承诺未兑现"补 edit_ops 或把决策改实；
- 未认领 diff region（WARN）→ 人工确认是否重排噪音，结论写入 manual_confirmations.json；
- 承诺"无法判定" → 列入 uncertainty.json，回复信中主动说明；
- verify_revision FAIL → 按其 checks 定位修复后重跑。
