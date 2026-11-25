# 表 1 · 提交台账（写作13｜LaTeX 写作与编译，product-arena-07-865de7e4）

采集时间：2026-11-23 UTC（2026-11-24 复核：90654=38.33、90655=55 维持 scored；90648/90650/90653/101508/101509/101511/101513 仍 evaluation_error/pending_review）。平台复核命令：`playground status --attempt-id <ID>` 与
`playground attempt list --challenge-id product-arena-07-865de7e4 --limit 50`（platform_verified）。

| 版本 | 目录 | 方向 | attempt | 提交时间 | 状态 | 得分 | 置信度 |
|-|-|-|-|-|-|-|-|
| （外部提交，仓库无对应版本） | — | 未知（harness: DeepSeek Harness 0.1.1-rc.2，model: grok-bot-c13-latex-v1） | 65658 | 2026-11-07 | scored | 56 | platform_verified |
| （外部提交，仓库无对应版本） | — | 未知（harness: codebuddy-cli） | 66101 | 2026-11-08 | scored | 58.67 | platform_verified |
| （外部提交，仓库无对应版本） | — | 未知（harness: codebuddy-cli） | 66367 | 2026-11-08 | scored | **68** | platform_verified |
| （外部提交，仓库无对应版本） | — | 未知（harness: codebuddy-cli） | 66474 | 2026-11-08 | scored | 57 | platform_verified |
| v1.0.0 | LaTeX 写作与编译/v1.0.0 | 编译错误诊断与迭代修复闭环 | 90648 | 2026-11-19 | pending_review（evaluation_error，harbor_errors=0） | 未出分 | platform_verified（pending，不参与基线评选） |
| v1.0.1 | LaTeX 写作与编译/v1.0.1 | 公式一致性与排版合规 | 90650 | 2026-11-19 | pending_review（evaluation_error） | 未出分 | platform_verified（pending） |
| v1.0.2 | LaTeX 写作与编译/v1.0.2 | 表格与浮动体治理 | 90653 | 2026-11-19 | pending_review（evaluation_error） | 未出分 | platform_verified（pending） |
| v1.0.3 | LaTeX 写作与编译/v1.0.3 | 引用与参考文献收敛 | 90654 | 2026-11-19 | scored（outcome=partial） | 38.33 | platform_verified |
| v1.0.4 | LaTeX 写作与编译/v1.0.4 | 模板适配与可重复构建 | 90655 | 2026-11-19 | scored（outcome=partial） | **55** | platform_verified |

## 核对结论

- 平台共 9 次提交；仓库内仅 5 个版本目录（v1.0.0–v1.0.4），4 次早期提交（65658/66101/66367/66474）
  由其他 harness（codebuddy-cli / grok-bot）提交，**对应 Skill 内容不在本仓库也不可得**
  （bundleAvailable=null），记 `external_content_unavailable`。
- 仓库各版 `SUBMISSION.md` 仍写"待出分"（drift）：90654=38.33、90655=55 已出分，
  本次迭代回填；3 个 evaluation_error 版本仍 pending_review（2026-11-23 复核未变）。
- 台账最高分 = 68（attempt 66367，内容不可得，不能做代码超集基线）；
  **代码基线 = v1.0.4（55，内容可得版本中的最高分）**。
- 已出分版本得分来源全部为第 1 级（platform_verified），满足 §1.5 完成判据。

## 2026-11-24 · v2.0.4 复投登记

- **v2.0.4 = attempt 103605**（2026-11-24T07:01:44+00:00 submitted）。
- 决策依据：全部 9 次历史提交复核——仅 90654=38.33、90655=55 出分；101508/101509/101511/101513
  execLog 明示 `Standalone evaluation failed: JudgeUnavailable`（harbor_errors=0，平台侧，非 Skill 缺陷）；
  外部 4 次（56–68）均 outcome=partial → partial 非区分因素，内容质量才是。
- 父版 = v1.0.4（55，内容可得最高分）；唯一机制改动 = instruction_audit（与未获评分
  的 v2.0.0 等价，命中有实跑证据的题面指令漏检短板，归属实际效果 40 分维度）。
- 回归 verdict=pass（语法/引擎指令捕获正误双向/全链路 validate PASS；沙箱缺 pdflatex
  中文字体为环境限制，审计如实报 fail，符合设计）。

## 2026-11-24 · 第二次复核（10 次提交）

- 103605（v2.0.4）execLog：`Standalone evaluation failed: JudgeUnavailable`，harbor_errors=0，
  与 v2.0.0–v2.0.3 同一平台侧故障；2026-11-24 复核未出分。
- 平台实况不变：仅 90654=38.33、90655=55 两次出分（均为 11-19 提交）；
  11-23 起全部 5 次提交（101508/101509/101511/101513/103605）均 JudgeUnavailable，
  判定为本题评测器自 11-23 起持续不可用，复投无效，待平台恢复后再查。

## 2026-11-25 · 第三次复核（10 次提交）

- 10 次提交状态与 11-24 完全一致：仅 90654=38.33、90655=55 出分；其余 8 次仍 evaluation_error。
- 本题评测器自 11-23 起持续 JudgeUnavailable 已达第三天，维持"暂停提交、定期查分"判定。

## 2026-11-25 · 五方向批次 v2.1.0-v2.1.4 提交登记

- 父版 = v1.0.4（90655，55 分，唯一内容可得最高分）；每版相对父版仅一处机制增量，
  五方向按 EV 排序：①instruction_audit ②fast_lane ③template_fix ④pdf_extract ⑤math_audit。
- v2.0.0-v2.0.4 机制从未获评分（JudgeUnavailable），v2.1.0 为 instruction_audit 复投，
  v2.1.1-v2.1.3 复用已回归的同机制资产，v2.1.4 为全新方向（math_audit，M1-M8）。
- 提交（2026-11-25T02:49Z 顺序）：v2.1.0=106397、v2.1.1=106401、v2.1.2=106403、
  v2.1.3=106410、v2.1.4=106411，均 submitted。
- 回归 verdict=pass（各自代理 case 实测：引擎指令捕获/最小闭环 validate PASS/
  epsfig→graphicx 修复后 0 错收敛/PDF-only 骨架生成/M 类 findings 7 项带定位）。
- 说明：attempt↔版本映射按提交时间顺序（attempt list 新→旧）对应版本 ④③②①。
