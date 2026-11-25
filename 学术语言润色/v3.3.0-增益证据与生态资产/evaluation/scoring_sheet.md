# 学术语言润色评分表（可复用 rubric）

对照"改得对 / 说得像 / 没改坏 / 讲得清"四问与运行证据评分。每项给出检查点与取证位置。
可用于任意稿件的润色质量评审（人工或 Agent 自评）。

## A. 改得对（硬错误消除，30%）

| 检查点 | 取证 |
|-|-|
| 语法/句法/搭配/标点错误逐句清点，改后复检为零 | change_log types 分布 + 抽样复读 |
| 无"掩盖式改法"（换说法但错误仍在，如 a accuracy → a accurate） | 阶段5回读 |
| 长句切分后逻辑关系保留 | change_log long-sentence 类逐条看 |

## B. 说得像（文体与术语，25%）

| 检查点 | 取证 |
|-|-|
| 语域贴合目标文体（无口语化/宣传化/人称误用） | style_guides.md 检查清单逐条过 |
| 术语全篇统一（同概念一种写法） | terminology check critical=0 |
| 缩写首现规范 | consistency_report warning=0 |

## C. 没改坏（语义与事实守恒，25%）

| 检查点 | 取证 |
|-|-|
| 数值/单位/统计量逐句一致 | guard_report numbers=0 |
| 引用编号与图表指向一致 | guard_report citations/pointers=0 |
| 限定强度、否定范围、因果性质不变 | guard_report hedging/negation/causality=0 |
| 无整段重写（修改幅度与理由匹配） | change_log 抽样；改后长度比 |

## D. 讲得清（可核验性，20%）

| 检查点 | 取证 |
|-|-|
| 每处修改有原文/改文/类型/理由 | change_log.jsonl schema 校验 |
| 第三方可逐条判断该不该改（理由具体、非套话） | reason 抽样评审 |
| 未决项与材料缺口显式标注 | result.json uncertainty/manual_review_required |
| 关键标记有处置记录 | resolutions.jsonl |

## 计分建议

每检查点按 0（缺失）/1（部分）/2（完备）计，维度内取均值×权重；总分映射：
≥90 优秀（可直接进入下一轮写作）；75–89 良好（少量人工复核）；60–74 合格（需返工条目）；
<60 不合格（存在守恒破坏或整段重写，须重跑）。

## 对照实验设计（验证 Skill 增益）

- 同一原文、同一术语表、同一评分人，分别评 基础 Agent 输出 与 Skill Agent 输出，
  盲评更佳（隐去来源标签）。
- 记录：人工返修条目数、逐句核对条目数、达到"可提交"状态的轮次。
