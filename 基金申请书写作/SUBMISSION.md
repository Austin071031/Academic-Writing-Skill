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

## v2.0.x 五方向单点迭代批次（父辈 v1.0.3 / 90810 / 66.67，2026-11-25 提交，待出分）

迭代协议：资产守恒（父辈 13 脚本 md5 一致，引擎零改动）、打包守恒（唯一文件 21–22 个）、
每版只改一处针对评分摘要（"more complete, genuinely-derived solution"）的提分点；
回归证据见各版本目录 `regression_report.json`（机器真跑生成）。

| Attempt | 版本 | 单点改动（唯一一件事） | 命中维度 | 状态 |
|-|-|-|-|-|
| 106566 | v2.0.0-快速主通道 | sections_scaffold 骨架预生成（含 FID 候选与字数目标）+ SKILL.md 8 步主通道与 ≤40 请求预算表 | 实际效果（截断→partial 治理） | submitted |
| 106567 | v2.0.1-示例成稿锚定 | 新增 2983 字完整合成成稿 exemplar（七要素达标厚度+标记密度示范），写作步首句锚定 | 实际效果（厚度/体裁） | submitted |
| 106568 | v2.0.2-契约自动对齐 | contract_check 逐字段语义映射机检 + assemble_result 回填补丁 | 任务完成度/可核验 | submitted |
| 106569 | v2.0.3-厚度信息密度 | elements_check 阈值上提+FID 密度机检+可执行扩展指令，扩展环改强制 | 完整性/正确性 | submitted |
| 106570 | v2.0.4-增益自评卡 | gain_card 反事实缺陷对照+修订闭环+机械劳动量化，嵌入 report | 使用增益可验证/创新证据 | submitted |

- 出分后将回填本表与各版本 SUBMISSION.md；若某方向显著提分，下一批以该方向为新父辈。

