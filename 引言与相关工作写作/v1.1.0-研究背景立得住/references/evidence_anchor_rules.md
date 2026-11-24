# 证据锚点与自动绑定规则（v1.1.0）

## evidence_map.json 字段

| 字段 | 说明 |
|---|---|
| eid | E1、E2……连续编号 |
| type | finding（他人/材料事实）｜limitation（已引工作局限）｜result（本文结果）｜meta（文献元数据）｜judgment（作者判断） |
| source.kind | manuscript（稿件段落）｜note（阅读笔记）｜library（文献条目） |
| source.loc | P###（稿件段号，见 manuscript.json）／N###（笔记段号）／R###（文献条目号） |
| quote | ≤200 字摘录；数字必须与原材料一致 |
| numbers | quote 中出现的数字列表（供泄漏检查） |
| cite | **v1.1.0 关键字段**：该证据对应的文献条目号（library.json 的 id），可多选；他人工作的证据必填，本文结果/作者判断留空 [] |
| note | 一句话说明该证据支撑什么 |

## 自动绑定（锚点即绑定，v1.1.0 起）

- 草稿句末挂 〔E#〕，且该 E 的 cite 非空 → 引擎自动为该句注入 [n]（同句多 cite 合并 [n,m]）。
- claim_bindings.jsonl 已废弃：无需登记绑定句，引擎直接从草稿锚点派生。
  （文件若存在仍被兼容读取，但重复登记可能重复注入，建议不写。）
- 编号由引擎按首次出现顺序分配（先引言后相关工作）；注入位置为句末标点之前。
- 工作稿中手写 [n] 会被检出（agent_pre_numbered），需删除后重跑。

## 自查

- build_report.json 的 bindings.auto_derived 应 ≥ 实际被引用的句数；
- references.md 条数 = 实际被引文献数；
- 某句引用未注入 → 依次检查：锚点存在？eid 在 evidence_map 中？cite 非空？条目在 library.json 中？
