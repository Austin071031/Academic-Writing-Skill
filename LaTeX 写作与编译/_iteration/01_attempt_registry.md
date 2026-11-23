# 表 1 · 提交台账（写作13｜LaTeX 写作与编译，product-arena-07-865de7e4）

采集时间：2026-11-23 UTC。平台复核命令：`playground status --attempt-id <ID>` 与
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
