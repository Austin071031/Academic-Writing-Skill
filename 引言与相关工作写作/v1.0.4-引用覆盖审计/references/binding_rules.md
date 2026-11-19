# 论断-引用绑定细则（双向）

## claim_type 选择

| claim_type | 用于 | entry_ids 要求 |
|---|---|---|
| others_result | 转述他人结论 | ≥1 |
| quantitative_fact | 他人工作的具体数字 | ≥1 |
| method_lineage | 方法沿袭（"采用 X 提出的"） | ≥1 |
| survey_coverage | 单篇综述/范围覆盖 | ≥1 |
| group_overview | 一组文献的概括（"已有工作普遍…"） | ≥2 |
| comparison | 与本文/跨组比较 | ≥1 |
| own_result | 本文结果（挂本文证据） | 可 0（须给 eids） |
| transition | 过渡句 | 不写 binding |

## naked_claims 的产生与消除

引擎把"写了 binding 但 entry_ids 为空（非 own_result/transition）"或
"group_overview 只有 1 条"的句子列为 naked_claims。消除方式：

1. 补引用：找到支撑该句的条目，填 entry_ids；
2. 改类型：若是单篇转述误标 group_overview，改成 others_result；
3. 删除：若是过渡句却误写了 binding，整行删除。

## 引用位置纪律

- 引用注入在论断句末（引擎完成），禁止段末集中堆放；
- 一篇文献支撑多个论断时，在每个论断句各绑一次（引擎会合并为同号多标记）；
- 一句多源时 entry_ids 写多条，引擎合并为 [n,m]。
