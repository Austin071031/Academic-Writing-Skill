# 自查评分表（对应赛题维度）

| 维度 | 自查项 | 证据 |
|-|-|-|
| 任务完成度 | rewrite.md 为完整成稿、符合文体与篇幅 | rewrite.md + inspection |
| 结果正确性 | 数据/单位/图表编号与源文逐值一致；无源外数值 | fidelity_report（exit=0）+ evidence_map |
| 结果完整性 | 关键结论/数据保留；删除有理由且列出丢弃事实 | retention_ledger + change_log |
| 可核验性 | 逐条来源映射、换算式、逐段台账 | fidelity_report + retention_ledger + evidence_map |
| 质量增益 | critical 清零；warn 逐条处置 | check exit=0 |
| 效率增益 | 逐值比对/台账校验秒级完成，人工仅需改稿 | stats.json |
| 创新 | 正向保真+反向溯源+图表一致性+取舍台账四重核验 | fidelity_engine.py |
| 稳定 | 重复运行结果一致；遮蔽防误报；异常有降级路径 | exceptions + 遮蔽统计 |
| 生态 | 判据表/失败模式/worked example 可复用 | references/ |

## 实测记录（合成案例 syn-w17-001，2026-11-19）

| 用例 | 命令 | 结果 |
|-|-|-|
| 正例改写稿 | `fidelity_engine.py check` | verdict=PASS，exit=0（verbatim 7，critical 0） |
| 反例：85.3%→89% + 新增"提升 40%" | 同上 | verdict=FAIL，exit=2（altered 1 + unverified 2，全 critical） |
| 反例：derived 换算稿（0.005 μm/0.853/73%，漏 320 Ω） | 同上 | verdict=FAIL，exit=2（derived 5 换算式正确；320 Ω missing= critical） |
| 正例台账 | `fidelity_engine.py ledger` | OK，exit=0（决定 5，覆盖关键段 3） |
| 反例台账：删除关键段无理由 + 缺决定 | 同上 | FAIL，exit=2（unreasoned_action + missing_decision，列出缺失 pid） |
| 反例台账：文件缺失 | 同上 | FAIL，exit=2（decisions_file_missing，列出全部缺失 pid） |
| 收尾 | assemble → validate → render | exit=0 / 0 / 0 |
