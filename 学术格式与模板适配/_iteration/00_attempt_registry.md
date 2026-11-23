# 表 1 · 提交台账（学术格式与模板适配 / challenge-96263d10）

采集时间：2026-11-23 UTC。平台复核命令：`playground status --attempt-id {ID}`。

| 版本 | 目录 | 方向 | attempt | 提交时间 | 状态（平台实查） | 得分 | 置信度 |
|-|-|-|-|-|-|-|-|
| v1.0.0 | 学术格式与模板适配/v1.0.0 | 模板适配全流水线 | 89023 | 2026-11-19T04:56:51Z | `evaluation_error`（harbor_errors=0，countsTowardQuota=false，score_is_final=false） | 无 | `platform_verified` |
| v1.0.1 | 学术格式与模板适配/v1.0.1 | 同上 + 契约字段语义映射 | 89028 | 2026-11-19T05:01:19Z | `evaluation_error`（同上签名） | 无 | `platform_verified` |

## drift 记录

- 仓库 `v1.0.0/SUBMISSION.md`、`v1.0.1/SUBMISSION.md`（提交号登记 commit ec36a5a 写入）状态为"待人工评审／待出分"；平台实查为 `evaluation_error`（worker 故障签名，非人审）。**以平台为准**，本次迭代须回填更正（记 `drift`）。
- 平台同窗口（11-19 11:34 起）他人提交正常出分，确认两次失败为平台故障波命中，非本 Skill 内容失败。

## 参考（非本账号，仅作分带背景，不作裁决依据）

公开榜当前版本案例分数带约 57–65.33（最高 Peter 82074 = 65.33）；73652/74032 的 83.0 为 11-13 案例改版前历史成绩。来源：平台公开 attempts 接口，`platform_verified`，但属于他人提交，**不进入本题基线评选与方向裁决**。

## 结论

- 共 2 版，**已出分 0 版**，无最高分基线可立。
- 基线评选：无 `repo_verified` 以上得分证据 → 按 §阶段 4 分支"全部 pending → 契约层修复版"处理，禁止方向迭代。
