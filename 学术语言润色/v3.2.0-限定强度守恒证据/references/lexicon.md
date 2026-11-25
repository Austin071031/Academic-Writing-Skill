# 限定强度词表与禁动清单（lexicon）

## 限定强度三档（守恒自查的依据）

| 档 | 中文 | 英文 |
|-|-|-|
| 强（0） | 证明、证实、确证、必然、肯定、毫无疑问、首次证明 | prove, confirm, definitively, establish, always, must, undoubtedly |
| 中（1） | 表明、显示、说明、揭示、反映出、显著（统计义）、一致表明 | suggest, indicate, show, demonstrate, reveal, support, consistent with |
| 弱（2） | 可能、或许、有望、提示、倾向于、初步、约、大致、一定程度上、不完全 | may, might, could, possibly, potentially, likely, appear, seem, tend, preliminary, approximately, roughly, partially |

**规则**：不得跨档替换（0→1 是削弱作者主张，2→0 是偷偷加强结论，都算改坏）；
不得静默删除任何限定词；同档替换（may→might）允许但理由注明"同档替换"。

## 因果与相关（不可互换）

因果：导致、引起、决定、致使、归因于、使得 / cause, lead to, result in, due to, attributable to。
相关：相关、关联、伴随、对应、一致 / correlate, associate, consistent with, in line with。
修改句式时保持原逻辑性质；"相关"改"导致"是事实性改动。

## 否定与量词

不/未/无/没有/并非 / not, no, never, without, fails to：增删任一个都可能改变命题真值。
所有/全部/均 ↔ some/several/部分："所有体系"改"多数体系"是主张范围变化。
（注意："非常"不是否定；"并非/无非/并非所有"才是。）

## 禁动清单（逐字保留）

- 数值与小数点、单位（% ℃ nm μm eV kPa p 值 R² 置信区间）
- 引用编号 [1] [1,2] [1-3]、（作者， 年份）、\cite{key}、\ref{}、\label{}
- 图/表/公式/章节编号（图3、Table 2、Eq. (4)、第2.3节）
- 专有名词拼写与大小写（方法名、蛋白名、数据集名）
- 数学公式与单位记号整体
