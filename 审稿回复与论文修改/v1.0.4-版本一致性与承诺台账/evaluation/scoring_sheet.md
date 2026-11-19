# 评分点-机制对照自查表（v1.0.4 版本一致性方向）

| 评分点 | 分值 | 本 Skill 对应机制 | 自查方式 |
|-|-|-|-|
| 任务完成度 | 15 | 八步管线交付修订稿+回复信+对账报告+承诺台账；init_result 骨架防超时空手 | result.json outputs 非空 |
| 结果正确性·对得上 | 15 | **声称-操作-差异三方对账**：op 落点强校验 FAIL"声称已改但无实际差异"；E# 引用逐项核验 | consistency_report 第 2 节全 ✅ |
| 结果完整性 | 5 | diff region 反向认领：未声明改动 WARN 列出，修订稿不存在回复信未交代的改动 | consistency_report 第 2.3 节 |
| 结果可核验性 | 5 | 差异区域带双侧行号与内容头；op→region 映射机器可读（consistency.json） | consistency.json op_region |
| 多轮承诺可追踪 | （融入对得上） | 承诺台账：嗅探历史回复、承诺句抽取、关键词重叠兑现判定、占位只记部分兑现 | revision_ledger.json |
| 质量增益 | 15 | 三方对账/未声明改动检出/跨轮承诺追踪为基础 Agent 不具备的结构化能力 | 对照平台白板 |
| 效率增益 | 5 | diff 与对账全脚本化（秒级），Agent 只做复核与决策 | 脚本时间戳 |
| 增益可验证 | 5 | 同一管线可复跑，中间 JSON 全量保留 | work/ 目录 |
| 新增能力 | 5 | 行级 diff region 对账 + 承诺台账跨轮追踪 | consistency_rules.md 第 1/4 节 |
| 方法改进 | 5 | 落点强校验（区域内部而非全稿子串）+ 噪音自动豁免 | consistency_rules.md 第 2/3 节 |
| 创新证据 | 5 | 合成示例端到端可复跑（含假上轮承诺检出演示） | examples/minimal_example.md |
| 调用易用 | 3 | SKILL.md 命令逐条可复制；--baseline/--case/--input-dir 兜底 | docs/USAGE.md |
| 运行稳定 | 4 | 纯标准库零依赖；幂等全量重算；多编码容错读取 | 重复运行结果一致 |
| 异常处理 | 3 | 10 类异常处置表（历史缺失/重排噪音/承诺无法判定/占位兑现…） | SKILL.md 第 4 节 |
| 文档完整 | 3 | README/USAGE/CHANGELOG/schemas/consistency_rules/示例齐备 | 本目录 |
| 资源复用 | 4 | 对账规则/承诺词表/命名约定/台账模板可直接复用 | references/, templates/ |
| 分享价值 | 3 | 三方对账模型与承诺判定阈值沉淀为显式规则 | consistency_rules.md |
