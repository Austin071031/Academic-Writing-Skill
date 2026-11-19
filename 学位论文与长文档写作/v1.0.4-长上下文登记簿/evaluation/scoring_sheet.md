# 自查评分表（对应题面评分维度）

| 评分项 | 自查问题 | 本 Skill 机制 |
|-|-|-|
| 任务完成度 15 | 是否真正写出不脱节的新章节而非写作建议？ | Phase 3 按 context_brief 成稿；Phase 4 overlap 复核闭环，critical 清零才交付 |
| 结果正确性 15 | 术语/结论/数值是否与前文一致？ | dossier 定义与结论登记逐条带 pid 溯源；重复结论同主语+关键数值双重判据 |
| 结果完整性 5 | 材料是否被遗漏？ | material_usage 矩阵 + omissions 清单；brief 与 overlap 双重「未用材料提醒」 |
| 结果可核验性 5 | 能否追溯到段落/阈值/截断？ | 全部条目带稳定 pid；阈值写入 dossier/overlap 报告；brief 末尾如实记录截断量 |
| 质量增益 15 | 相比基础 Agent 是否稳定提升？ | 基础 Agent 通读不进数万字全文→凭印象写→脱节/重复；本 Skill 登记簿+复核，缺陷稿三项注入缺陷全部检出 |
| 效率增益 5 | 是否减少上下文占用？ | **Agent 全程不需要通读全文**：写作只读 ≤3000 字符的 context_brief + 分节可读的 dossier.md，显著低于全文 token |
| 新增能力 5 | 基础 Agent 不具备的能力 | 句子级 4-gram 重复论述检测、同主语重复结论检测、术语首现早于定义的脱节候选、悬空图表引用检测 |
| 运行稳定性 4 | 不同章节类型/篇幅/重复运行 | 纯标准库、幂等重跑；骨架 result 防空手；40 请求预算兜底 partial |
| 异常处理 3 | 材料识别失败/定义为空/预算截断等 | SKILL.md 异常处置表 10 类；exceptions/manual_confirmations 如实登记，不静默 |
| 文档完整性 3 | 说明/示例/限制/失败模式 | README/USAGE/dossier_rules/failure_modes/minimal_example/test_texts 齐备 |
