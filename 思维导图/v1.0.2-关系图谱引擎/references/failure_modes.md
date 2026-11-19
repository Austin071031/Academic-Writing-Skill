# 失败模式与对策（v1.0.2）

| 失败模式 | 症状 | 对策 |
|-|-|-|
| 万物 supports | 所有边一个类型 | 按 relation_rules.md 线索细分；引擎词表外判 critical |
| 层级当关系 | 用父子表达因果 | 父子只表达包含/分类；因果放 edges |
| 无依据连边 | edge_no_evidence 大量出现 | 删边或标"推断"+uncertain |
| 数字矛盾被抹平 | 只写一方数字 | conflicts 边连接双方，各挂证据，标 uncertain |
| 方向写反 | depends_on 倒挂 | 对照方向规则；引擎双向冲突告警 |
| 同义数值误报冲突 | "50%" vs "0.5" | 人工核实后不连 conflicts，可在 note 说明 |
| 关系图当导图交 | 只交 relations.* | 层级六格式与关系三件套都要交 |
| 漏边不处理 | missing_relation_candidate 堆积 | 至少处理共享证据 ≥2 单元的节点对 |
