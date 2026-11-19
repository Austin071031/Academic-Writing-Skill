# 自查评分表（对应赛题维度）

| 维度 | 自查项 | 证据 |
|-|-|-|
| 任务完成度 | rewrite.md 为完整成稿、符合目标文体模板结构 | rewrite.md + genre_mapping.json |
| 结果正确性 | 数据/单位/图表编号与源文一致；无源外结论；引语未虚构 | evidence_map + alignment + ledger added_contains_number |
| 结果完整性 | 每个源文段落有去向；删除均有理由且删的是冗余 | traceability_report 表一 + change_reasons.jsonl |
| 可核验性 | 逐段对照台账两表齐全（源文→改写、改写→源文），含动作/理由/事实数 | traceability_report.md + change_ledger.json |
| 质量增益 | critical 清零（ledger exit=0）；warn 逐条处置 | change_ledger.json verdict |
| 效率增益 | 要素映射/对齐/台账生成秒级完成，人工仅需写稿与判断 | stats.json |
| 创新 | 文体模板要素映射 → 逐段理由 → 双向对照台账链条 | genre_mapping + change_ledger |
| 稳定 | 重复运行脚本结果一致；异常（文体未识别/要素缺失）有降级路径 | manual_confirmations + exceptions |
| 生态 | 4 套文体模板/理由格式/台账表结构可复用 | references/genre_templates.md |
