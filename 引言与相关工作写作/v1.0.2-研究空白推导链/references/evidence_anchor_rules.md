# 证据锚点与绑定规则

## evidence_map.json 字段

| 字段 | 说明 |
|---|---|
| eid | E1、E2……连续编号 |
| type | finding（他人/材料事实）｜limitation（已引工作局限）｜result（本文结果）｜meta（文献元数据）｜judgment（作者判断） |
| source.kind | manuscript（稿件段落）｜note（阅读笔记）｜library（文献条目） |
| source.loc | P###（稿件段号，见 manuscript.json）／N###（笔记段号）／R###（文献条目号） |
| quote | ≤200 字摘录；数字必须与原材料一致 |
| numbers | quote 中出现的数字列表（供泄漏检查） |
| note | 一句话说明该证据支撑什么 |

## claim_bindings.jsonl 字段

| 字段 | 说明 |
|---|---|
| loc | intro 或 rl（该论断出现在哪个工作稿） |
| sentence | 工作稿中逐字存在的句子（空白与全半角必须一致；可从工作稿复制） |
| entry_ids | 支撑该句的文献条目（library.json 的 id）；可多选 |
| eids | 该句挂的证据锚点（应与句中 〔E#〕 一致） |
| claim_type | others_result｜quantitative_fact｜method_lineage｜survey_coverage｜comparison｜own_result |

## 引擎核验口径

- 每个 〔E#〕 必须能解析到 evidence_map 条目，否则记 exceptions。
- 每个绑定句必须能在对应工作稿中定位（空白/标点差异容忍）；定位失败记 missed。
- 编号由引擎按首次出现顺序分配；同句多引合并为 [n,m]；注入在句末标点之前。
- 工作稿中手写 [n] 会被检出（agent_pre_numbered），需删除后重跑。
