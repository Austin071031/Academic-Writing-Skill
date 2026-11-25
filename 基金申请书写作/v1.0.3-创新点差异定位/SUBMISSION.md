# 提交与评分记录 — v1.0.3-创新点差异定位

| 项目 | 内容 |
|-|-|
| 赛题 | 写作14｜基金申请书写作（challenge-d403dce6） |
| 版本方向 | 说得准：不可核验修饰词黑名单（首次/国际领先/填补空白等）high 级检出 + 对比锚点与差异表述强制 |
| Attempt ID | 90810 |
| 提交时间 | 2026-11-19（UTC） |
| 提交方式 | `playground submit --challenge-id challenge-d403dce6 --outputs 基金申请书写作/v1.0.3-创新点差异定位 --skill 基金申请书写作/v1.0.3-创新点差异定位`（model/harness: SciMaster） |

## 评分结果（2026-11-25 查询）

| 字段 | 值 |
|-|-|
| 状态 | scored（scoreIsFinal=true） |
| **最终得分** | **66.67 / 100** |
| harbor_score | 66.67（scored_by playground-worker/harbor-lbg） |
| GitHub 附加分 | 0 / 5（github_reason: not_found，平台未在预期位置找到链接，后续迭代排查） |
| 评分摘要 | "Received and graded in full. Partial credit — push your agent for a more complete, genuinely-derived solution." |

## 分析与迭代方向

- 距离 80 分目标差 13.33 分；评分渠道为 harbor worker 自动重放评分，摘要提示
  “更完整、更真实推导/产出的解决方案”。改进方向：章节稿厚度与对案例材料的实际贴合度、
  output_contract 逐字段语义化填充、运行时真实产物的可复核完整性。
- GitHub 附加分本次计 0（not_found）；后续提交排查平台对 GITHUB_URL.txt 的读取位置，
  并考虑同时使用仓库根链接。

> 本文件随评分更新；历史得分以赛题平台为准。
