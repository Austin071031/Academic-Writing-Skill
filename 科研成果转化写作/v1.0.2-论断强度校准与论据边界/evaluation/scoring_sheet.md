# 自查评分表（对应赛题维度）

| 维度 | 自查项 | 证据 |
|-|-|-|
| 任务完成度 | rewrite.md 为完整成稿、符合受众与文体 | rewrite.md + inspection |
| 结果正确性 | 论断强度/因果性/否定极性与源文同级；无源外新结论 | claim_report（critical=0）+ evidence_map |
| 结果完整性 | 关键论断与限定条件保留；删除的是冗余 | source_claims vs claim_verdicts（无 missing）+ change_log |
| 可核验性 | 逐条论断来源映射、引擎核查报告 | claim_report.md + claim_verdicts.jsonl |
| 质量增益 | critical 清零；warn/info 逐条处置 | check exit=0 |
| 效率增益 | 论断抽取与比对秒级完成，人工仅需改稿 | stats.json |
| 创新 | 强度阶梯 L0-L3 + 因果标记 + 否定极性 + 反向 new_claim 检测链条 | source_claims / claim_report |
| 稳定 | 重复运行脚本结果一致；异常有降级路径（含源文论断自相矛盾处置） | exceptions / manual_confirmations |
| 生态 | 强度阶梯表、判定规则、失败模式可复用 | references/ |
