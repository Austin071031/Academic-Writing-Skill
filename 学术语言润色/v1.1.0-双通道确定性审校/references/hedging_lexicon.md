# 限定强度词表与守恒规则（hedging lexicon）

guard_check.py 用本词表做机械守恒检查（档位 0 强 / 1 中 / 2 弱）。Agent 逐句润色时
**不得跨档替换**；同档替换（may→might）允许但应在 reason 中注明"同档替换"。

## 档位 0（强断言）

中文：证明、证实、确证、必然、肯定、毫无疑问、决定性、首次证明
英文：prove/proves/proved/proven、confirm/confirms、definitively、establish/establishes、
always、must、undoubtedly

## 档位 1（中等：证据支持但留有常规余地）

中文：表明、显示、说明、揭示、反映出、显著（统计义）、一致表明
英文：suggest(s/ed)、indicate(s/d)、show(s/ed/shown)、demonstrate(s/d)、reveal(s/d)、
support(s/ed)、consistent with、in line with、confirmatory

## 档位 2（弱：假设、倾向、初步证据）

中文：可能、或许、有望、提示、倾向于、初步、约、大致、一定程度上、不完全、疑似、或将
英文：may、might、could、possibly、potentially、likely、appear(s)、seem(s)、tend(s)、
suggestive、preliminary、approximately、roughly、partially、in part

## 守恒规则

1. **禁跨档**：任何把 0→1/2（弱化作者主张）或 2→1/0（偷偷加强结论）的替换都是
   critical 错误。把"有望"改成"表明"、把 *suggests* 改成 *proves* 都属于此类。
2. **禁静默删除**：删除限定词（约、可能、partially）视同跨档弱化。
3. **同档替换要留痕**：may→might、可能→或 属可接受，reason 写明"同档替换"。
4. **证据动词与名词分档一致**：*results suggest* 与 *suggestive results* 等价；
   改句式时保持档位。
5. **统计显著性**：*significant(ly)* 作统计术语只在有检验语境时出现；中文"显著"
   若无统计含义（"显著提高"的日常义）按原文语义保留，不擅自改"统计显著"。

## 否定、量词与因果（同属守恒范围）

- 否定词（不/未/无/没有/并非/not/no/never/without/fails to）：增删任一个都可能改变
  命题真值 → critical。
- 量词：所有/全部/均 ↔ some/several/部分；"所有体系"改"多数体系"是主张范围变化 → critical。
- 因果 vs 相关：导致/引起/决定/致使/归因于/cause/lead to/due to ↔ 相关/关联/伴随/
  correlate/associate/consistent with。两类不得互换；修改句式时保持原逻辑性质。
  注意 *therefore/thus* 是话语连接词，不单独构成因果主张，与"导致"不同档处理。

## 典型错误与处置

| 原文 | 错误改法 | 正确处置 |
|-|-|-|
| 该方法**有望**用于药物设计 | 该方法**可用于**（2→1 加强） | 保留"有望"，或改"可能有助于"（同档） |
| 结果**表明** | 结果**证明**（1→0 加强） | 保留"表明" |
| *suggest* a link | *prove* a link | 保留 *suggest* |
| *approximately* 15% | 15%（删限定） | 保留 *approximately* |
| A **correlates with** B | A **causes** B | 保留相关表述，或"提示 A 可能与 B 相关" |
