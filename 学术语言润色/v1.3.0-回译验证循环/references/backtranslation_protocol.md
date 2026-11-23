# 回译验证协议（back-translation protocol）

## 目的

润色后语义漂移检测：改文"听起来对"不等于"还是同一句话"。回译把判断客观化：
译文与原文在同一张主张矩阵上逐格比对。

## 适用对象

关键句 = 含数值、单位、引用编号、图表指向、限定词、否定词或因果词的句子
（segment_util.py 已在 source_dump.md 用【K】标注）。非关键句 modify 不需回译。

## 步骤

1. **回译**：把 polished 句译回源语言。英改中→译回中文；中改英→译回英文；
   纯中文稿→用另一种规范中文重述（同义改写回读）；纯英文稿→换句式重述。
   回译追求忠实，不追求漂亮。
2. **填矩阵**：为原文与回译文各填一行（写入 chunk 行 claims 字段）：

| 格 | 取值示例 |
|-|-|
| hedging | 强档（证明）/ 中档（表明）/ 弱档（可能）/ 无限定词 |
| numbers | 15%（原样照抄，不含单位时写数值） |
| units | % 或 nm 等 |
| citations | [1]、[1,2]、\cite{zhang2020}、（作者, 2023） |
| pointers | 图2、Table 3、Eq. (4) |
| causality | 因果 / 相关 / 无 |
| negation | 有（并非所有）/ 无 |

3. **比对**：七格全等 → reason 末尾加"回译一致"。有差异 → 修 polished 再回译；
   两轮仍不一致 → decision 改回 keep、reason 写"回译漂移，回退保留原文"、
   句 ID 进 result.json manual_review_required。

## 档位判定规则（hedging 格）

- 出现"证明/证实/prove/confirm/establish" → 强档；无更强词时"表明/显示/suggest/
  indicate/show/demonstrate" → 中档；无更强词时"可能/有望/约/may/might/could/
  approximately" → 弱档。同句多词按最强者定档。
- 同档词替换（may→might）不算漂移；跨档即漂移。

## 典型漂移与处置

| 原文 | 改文（病灶） | 回译发现 | 处置 |
|-|-|-|-|
| 误差降低了约15% | 误差降低了15% | 回译丢"约" | 补回"约/approximately" |
| 结果与X相关 | 结果由X导致 | 回译成因果 | 改回相关表述 |
| suggests | indicates | 同档，不算漂移 | 放行，reason 注"同档替换" |
| 并非所有样本 | 所有样本 | 回译丢否定 | 修复否定或回退 |
