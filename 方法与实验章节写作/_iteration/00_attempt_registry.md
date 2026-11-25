# 表 1 · 提交台账（方法与实验章节写作 / product-arena-05-64faa4a2）

复核时间：2026-11-23（UTC）。复核命令：`playground status --attempt-id <ID>`（§0-10）。

| 版本 | 目录 | 方向 | attempt | 提交时间 | 状态 | 得分 | 置信度 |
|-|-|-|-|-|-|-|-|
| v1.0.0 | v1.0.0-证据锚定双向溯源 | 证据锚定双向溯源（正向泄漏+反向闭合审计） | 89818 | 2026-11-19T09:08:48Z | execStatus=failed，harbor_status=evaluation_error | 无分（0 为占位显示） | platform_verified |
| v1.0.1 | v1.0.1-六要素阶段矩阵 | 要素×train/val/test 18 格覆盖+串台检测 | 89821 | 2026-11-19T09:1x | execStatus=failed，evaluation_error | 无分 | platform_verified |
| v1.0.2 | v1.0.2-可复现命令链 | 复现七要素闸门+命令入章校验 | 89823 | 2026-11-19T09:2x | execStatus=failed，evaluation_error | 无分 | platform_verified |
| v1.0.3 | v1.0.3-跨源一致性核验 | 多源取值机检+三级裁决闭环 | 89824 | 2026-11-19T09:2x | execStatus=failed，evaluation_error | 无分 | platform_verified |
| v1.0.4 | v1.0.4-对照实验统计口径 | 实验矩阵+可比性闸门+措辞三档 | 89826 | 2026-11-19T09:2x | execStatus=failed，evaluation_error | 无分 | platform_verified |

## 旁证（同账号、同分钟级窗口，写作10 / product-arena-06-caca73b2）

| attempt | 状态 | 得分 | 包形态 |
|-|-|-|-|
| 89797 | completed/scored | 67.3333 | 11 个文件、60KB、无 submission/ 镜像 |
| 89798 | failed | evaluation_error | 同上形态（同会话同打包） |
| 89800 | completed/scored | 68.6667 | 同上 |
| 89801 | completed/scored | 60.0 | 同上 |
| 89802 | completed/scored | 73.6667 | 同上 |

## 总量核对

- 平台本题总提交 616+ 次；本账号本题提交恰好 5 次（89818–89826），无遗漏、无 pending 出分。
- 关键推论：evaluation_error 非内容判 0（对比 99591–99597 是 completed 但 0 分），而是 replay 运行失败；
  同窗口 89798 证明该故障也击中形态正常的提交（间歇性），但本账号 5/5 全中，叠加因素疑似
  包内 UTF-8 文本文件总数（outputs/ + results/ 双份 = 66–70 个）超出契约"Skill resources: at most 50
  UTF-8 text files"（成功样本：写作10 22–27 个、63382 自述 31 个，均 <50）。
- scoring-log 端点对非组织方 403，失败内层日志不可得（已尝试 9 个端点，见会话记录）。

## v2.0.x 打包修复批次（2026-11-25 复核出分，platform_verified）

| 版本 | 目录 | 方向 | attempt | 提交时间 | 状态 | 得分 | 置信度 |
|-|-|-|-|-|-|-|-|
| v2.0.0 | v2.0.0-证据锚定双向溯源-打包修复 | 同 v1.0.0（打包修复） | 101409 | 2026-11-23T13:35:08Z | scored/final | 62.0 | platform_verified |
| v2.0.1 | v2.0.1-六要素阶段矩阵-打包修复 | 同 v1.0.1（打包修复） | 101410 | 2026-11-23T13:35:10Z | scored/final | 62.0 | platform_verified |
| v2.0.2 | v2.0.2-可复现命令链-打包修复 | 同 v1.0.2（打包修复） | 101411 | 2026-11-23T13:35:11Z | scored/final | 62.6667 | platform_verified |
| v2.0.3 | v2.0.3-跨源一致性核验-打包修复 | 同 v1.0.3（打包修复） | 101412 | 2026-11-23T13:35:13Z | scored/final | 62.0 | platform_verified |

出分事实修正两处既有推断：① 打包修复生效（evaluation_error 消除，4/4 出分），
证实 v1 弃权主因是包内文本文件超 50；② v2 得分 62–62.67 显著低于本题公开出分带
78.67–81.0，说明 v1.0.x 内容层存在真实短板（待按迭代协议做方向层分析，本轮仅回填）。
