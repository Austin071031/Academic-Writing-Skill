# 学术翻译与双语写作（写作12｜challenge-bb17a294）提交总览

5 个版本对应题面五大突破方向，共用句段级翻译管线（脚本承担机械劳动、Agent 只做
翻译与判断、机检—修订闭环、诚实降级）。各版本详细评分见各自目录下 `SUBMISSION.md`。

## 评分状态（2026-11-25 查询，scoreIsFinal 为准）

| Attempt | 版本 | 方向 | 得分 | 状态 |
|-|-|-|-|-|
| 90668 | v1.0.0-术语一致性锁定 | 术语稳 | — | pending_review（未出分） |
| 90669 | v1.0.1-数字单位忠实 | 数字实 | **58 / 100** | scored（final） |
| 90670 | v1.0.2-双语句段对齐 | 对得齐 | — | pending_review（未出分） |
| 90671 | v1.0.3-学术风格控制 | 学术风格 | **58 / 100** | scored（final） |
| 90672 | v1.0.4-引用语义边界 | 边界清 | **57 / 100** | scored（final） |

- 评分渠道：playground-worker/harbor-lbg 自动重放评分；三者 GitHub 附加分均暂计 0
  （submitted_artifact_needs_review，待人工复核）。
- 目标 ≥80 分：当前最高 58，差距主要在“完整、真实推导的交付物”维度
  （评分摘要：Partial credit — push for a more complete, genuinely-derived solution）。
- 未出分版本（90668/90670）出分后将补登本表与对应 SUBMISSION.md。

> 查询命令：`playground status --attempt-id <id>`
