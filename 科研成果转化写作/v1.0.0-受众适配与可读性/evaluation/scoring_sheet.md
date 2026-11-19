# 自查评分表（对应赛题维度）

| 维度 | 自查项 | 证据 |
|-|-|-|
| 任务完成度 | rewrite.md 为完整成稿、符合受众与文体 | rewrite.md + profile |
| 结果正确性 | 数据/单位/图表编号与源文一致；无源外结论 | evidence_map + alignment |
| 结果完整性 | 关键结论/限定条件保留；删除的是冗余 | change_log 删除理由 |
| 可核验性 | 逐条来源映射、引擎核查报告 | readability_report + evidence_map |
| 质量增益 | critical 清零；warn 逐条处置 | check exit=0 |
| 效率增益 | 机械核查秒级完成，人工仅需改稿 | stats.json |
| 创新 | 受众画像→术语计划→达标核查链条 | audience_profile |
| 稳定 | 重复运行脚本结果一致；异常有降级路径 | exceptions |
| 生态 | 阈值表/术语计划格式可复用 | references/ |
