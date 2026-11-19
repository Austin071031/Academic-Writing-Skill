# 自查评分表（对应赛题维度）

| 维度 | 自查项 | 证据 |
|-|-|-|
| 任务完成度 | rewrite.md 为完整成稿，术语全表锁定，多产物同口径 | rewrite.md + term_table.json |
| 结果正确性 | canonical 均有源文依据；不臆造全称；数据与源文一致 | evidence_map + manual_confirmations |
| 结果完整性 | 关键结论/限定条件保留；术语表覆盖全部缩写与高频术语 | change_log + term_table |
| 可核验性 | 审计报告逐条定位 file:rpid；术语统一改动有台账 | terminology_audit.md + change_log |
| 质量增益 | critical 清零（exit=0）；warn 逐条处置或改表重跑 | audit 运行记录 |
| 效率增益 | 异写检测/展开核查/跨文件比对全脚本化，秒级完成 | stats.json |
| 创新 | 机选草稿→Agent 审定→锁定表→跨文体联审链条 | term_table_draft vs term_table |
| 稳定 | 重复运行脚本结果一致；术语歧义有"保留源文+人工确认"降级路径 | exceptions / manual_confirmations |
| 生态 | 术语表 schema / 异写判据 / 跨文体策略可复用 | references/terminology_rules.md |
