# Worked Example（合成示例，非正式案例）

源文（硫化物固态电池论文节选，合成）：

> 本研究采用硫化物固态电解质（SSE）与 LiNi0.8Co0.1Mn0.1O2（NCM811）正极构建全固态电池。
> SSE 的离子电导率达 12 mS/cm，但固体电解质与正极之间的界面副反应限制了循环寿命。
> 通过原子层沉积（ALD）在 NCM811 表面包覆 5 nm 的 LiNbO3 缓冲层……

任务：改写为面向公众的科普文章（≤800 字）＋200 字新闻简报，两个产物术语必须统一。

## candidates 机选草稿（节选）

| term_id | canonical | variants | kind | first_expand |
|-|-|-|-|-|
| T001 | 硫化物固态电解质 | SSE、固体电解质、固态电解质、固体电解质体系、固态电解质体系 | acronym | true |
| T002 | NCM811 | LiNi0.8Co0.1Mn0.1O2 | symbol | false |
| T003 | LiNbO3 | — | symbol | false |
| T004 | 原子层沉积 | ALD | acronym | true |

检测依据：SSE 由"全称（缩写）"配对；"固态电解质/固体电解质"相似度 0.80 聚类入 variants；
NCM811 与其化学式由"化学式（牌号）"配对。

## Agent 审定

- T001 canonical 确认为"硫化物固态电解质"（源文全称），科普文章栏：首次"硫化物固态电解质（SSE）"
  并解释"一种用固体传导锂离子的电解质"；
- 删除机选噪声条目（如"包覆后电池"）；
- LiNbO3 无中文名，note 标"铌酸锂（通用中文名，已确认）"或入 manual_confirmations。

## 改写稿片段（正例）

> 全固态电池的核心部件之一是硫化物固态电解质（SSE）——一种用固体传导锂离子的电解质。
> SSE 的离子电导率高达 12 mS/cm，但它与 NCM811（一种镍含量较高的三元正极材料）接触时
> 会发生界面副反应……研究团队用原子层沉积（ALD）技术包覆 5 nm 厚的 LiNbO3（铌酸锂）缓冲层。

audit 结果：PASS（0 critical / 0 warn），双产物联审 PASS。

## 反例

草稿混用"固态电解质/固体电解质"且 SSE、ALD 未展开：
audit 判 2 critical（acronym_not_expanded: SSE@R002、ALD@R003）
+ 2 warn（variant_used: 固态电解质、固体电解质），exit=2，必须修复重跑。
简报改用"固体电解质"作为主导说法：cross_file_inconsistent = warn。
