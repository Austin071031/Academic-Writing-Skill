# 基金申请书写作（写作14｜challenge-d403dce6）提交总览

5 个版本对应题面五大突破方向（立得住 / 收敛 / 对得上 / 说得准 / 查得到），共用
"事实台账〔F〕〔拟〕〔确认〕标记 + 材料外事实机检 + 七要素三级对应 + 机检—修订闭环"
管线（脚本承担机械劳动、Agent 只做审定与写作、诚实降级）。各版本详细评分见各自目录下
`SUBMISSION.md`。

## 评分状态（2026-11-25 查询，scoreIsFinal 为准）

| Attempt | 版本 | 方向 | 得分 | 状态 |
|-|-|-|-|-|
| 90807 | v1.0.0-立项依据论证链 | 立得住 | **54.33 / 100** | scored（final） |
| 90808 | v1.0.1-科学问题收敛 | 科学问题收敛 | **55.67 / 100** | scored（final） |
| 90809 | v1.0.2-目标路线指标对应 | 对得上 | **66.00 / 100** | scored（final） |
| 90810 | v1.0.3-创新点差异定位 | 说得准 | **66.67 / 100** | scored（final） |
| 90811 | v1.0.4-研究基础证据链 | 查得到 | **53.67 / 100** | scored（final） |

- 评分渠道：playground-worker/harbor-lbg 自动重放评分，score_is_final=true。
- 评分摘要（各版本一致）："Received and graded in full. Partial credit — push your agent
  for a more complete, genuinely-derived solution."
- GitHub 附加分：5 个版本均暂计 0 / 5（github_reason: **not_found**——平台未在预期位置
  找到链接；本期 GITHUB_URL.txt 打包在 bundle 的 outputs/ 与 results/ 根，后续迭代需
  排查平台读取位置或改用仓库根链接后重新验证）。
- 目标 ≥80 分：当前最高 66.67（v1.0.3 创新点差异定位、v1.0.2 目标路线指标对应接近），
  差距主要在"更完整、更真实推导的交付物"维度——章节稿的厚度、对案例材料的实际贴合度
  与 output_contract 逐字段语义化填充是下一步迭代重点。
- 方向效果排序：说得准/对得上（66+）> 收敛（55.67）> 立得住（54.33）> 查得到（53.67）。

> 查询命令：`playground status --attempt-id <id>`
