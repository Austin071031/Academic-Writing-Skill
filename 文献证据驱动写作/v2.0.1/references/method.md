# 方法：原子论断切分与五值支撑匹配（claim-source-mapper）

## 原子论断切分规则
- 一条论断 = 一个可独立判定真伪/支持度的判断（一个主谓结构）；
- 数值、比较、因果、机制各自成条：“A 优于 B（n=120）”拆为“疗效比较”与“样本量来源”两条（后者是 metadata 型证据）；
- 禁止把背景、方法、结论塞进同一条；禁止复合句不拆；
- claim_text 用陈述句，可被第三方独立理解，不依赖上下文暗指。

## 五值支撑关系
| 关系 | 定义 | 对 status 的影响 |
|-|-|-|
| direct | 原文直接陈述该论断的内容（含数值一致） | 计入 supported |
| partial | 原文支持更弱/更窄版本 | 计入 partial |
| background | 仅背景相关，不构成支撑 | 不计入 |
| conflicting | 原文指向相反结论 | 置 conflicting |
| not_supporting | 看似相关实则不支持 | 记差异说明 |

## 多对多处理
- 一条论断需多篇支撑：全部列出，逐篇注明支撑的是论断的哪个分句（支撑范围精确到摘录内文句）；
- 一篇文献支撑多条论断：在 claim_source_matrix.csv 逐格标注关系，矩阵与 claims.jsonl/evidence.csv 双向一致（脚本检查）；
- 无支撑论断：status=unsupported，写入 open_questions，**绝不补造引用、不把 background 冒充 direct**。

## 与基础 Agent 的差异
基础 Agent 的“每句话有引用”停留在表面：引用常与句子内容只是话题相关。五值关系强制区分“相关”与“支撑”，
并允许复核者看到“支撑的是哪个分句”，这是本方向的增量能力。
