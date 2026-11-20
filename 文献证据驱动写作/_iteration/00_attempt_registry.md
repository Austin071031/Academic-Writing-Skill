# 表 1 提交台账（attempt registry）

赛题：challenge-b810ef56（写作05｜文献证据驱动写作）｜采集时间：2026-11-20
来源：源 C 平台实查（`curl /api/attempts/{id}`，2026-11-20 复核）× 源 B 各版 SUBMISSION.md 交叉核对 → 全部一致。

| 版本 | 目录 | 方向（direction.json） | attempt | 提交时间 | 状态 | 得分 | 置信度 |
|-|-|-|-|-|-|-|-|-|
| v1.0.0 | 文献证据驱动写作/v1.0.0 | evidence-extraction（证据提取） | 89151 | 2026-11-19T06:16:47Z | scored / partial | **66.3333** | platform_verified |
| v1.0.1 | 文献证据驱动写作/v1.0.1 | claim-source-linking（论断—来源关联） | 89152 | 2026-11-19T06:16:48Z | scored / partial | **70.0** | platform_verified |
| v1.0.2 | 文献证据驱动写作/v1.0.2 | citation-accuracy（引用准确性） | 89153 | 2026-11-19T06:16:49Z | pending_review（execStatus=failed） | 未出分 | platform_verified（**pending，不参与基线评选**） |
| v1.0.3 | 文献证据驱动写作/v1.0.3 | evidence-strength（证据强度） | 89154 | 2026-11-19T06:16:50Z | scored / partial | **63.0** | platform_verified |
| v1.0.4 | 文献证据驱动写作/v1.0.4 | uncertainty-expression（不确定性表达） | 89155 | 2026-11-19T06:16:51Z | scored / partial | **67.6667** | platform_verified |

核对结论：
- 平台上本账号（operatorId=674660）在本题仅有 89151–89155 五次提交，与仓库目录一一对应，无 drift、无漏记。
- 89153（引用准确性方向）execStatus=failed、待人工评审，无分数，按协议不参与基线评选；开工时已复查（2026-11-20），仍未出分。
- 四条已出分评语一致："Received and graded in full. Solid — refine for a more complete and rigorous solution."
- 台账最高分：**v1.0.1（claim-source-linking，70.0）** → 基线候选。
