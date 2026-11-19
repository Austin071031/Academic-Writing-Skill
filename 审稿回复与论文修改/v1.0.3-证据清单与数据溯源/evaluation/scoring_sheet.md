# 评分点-机制对照自查表

| 评分点 | 分值 | 本 Skill 对应机制 | 自查方式 |
|-|-|-|-|
| 任务完成度 | 15 | 八步管线交付修订稿+回复信+定位+证据清单+溯源报告；init_result 骨架防超时空手 | result.json outputs 非空 |
| 结果正确性（证得住） | 15 | 证据需求自动建档（EV 条目）；三档到位状态 Agent 终判；数字逐条溯源四档判定；未核实数字强制留痕 | evidence_checklist.json 状态分布；provenance_report.md |
| 结果完整性 | 5 | needs_evidence 子要求全部关联 EV；共享证据去重不遗漏 | 每条 EV 的 sub_ids 覆盖 comments 全部需证子要求 |
| 结果可核验性 | 5 | 数字溯源到 baseline P### 行号 / comments sub_id；evidence_map 自动建；输入文件 sha256 入 sources | provenance_report.md 逐行可点查 |
| 质量增益 | 15 | 证据建档/共享去重/数字溯源为基础 Agent 不具备的结构化能力 | 对照平台白板（无 EV 档案、数字无出处） |
| 效率增益 | 5 | 机械劳动脚本化（建档与全量数字比对秒级），Agent 只做终判与处置 | 脚本时间戳 |
| 增益可验证 | 5 | 同一管线可复跑；demand 重跑保留 Agent 修订，provenance 重跑幂等 | work/ 全量中间 JSON 保留 |
| 新增能力 | 5 | 数字级溯源 + 未核实自动进人工确认（exit=2 告警机制） | provenance exit code 与 manual_confirmations |
| 方法改进 | 5 | 证据状态"脚本初判 + Agent 终判"两段式；四档溯源判定优先级 | SKILL.md 步骤 4.5/7；evidence_rules.md |
| 创新证据 | 5 | 合成示例端到端可复跑（含共享 EV、未核实数字演示） | examples/minimal_example.md |
| 调用易用 | 3 | SKILL.md 命令逐条可复制；两阶段引擎参数一致（--work --out --stage） | docs/USAGE.md |
| 运行稳定 | 4 | 纯标准库零依赖；幂等可续跑；编码自动探测；exit=2 告警不硬失败 | 重复运行结果一致 |
| 异常处理 | 3 | 12 类异常处置表（初判仅供参考/意见给出不算未核实/占位与无法补做的区别…） | SKILL.md 第 4 节 |
| 文档完整 | 3 | README/USAGE/CHANGELOG/schemas/evidence_rules/模板/示例齐备 | 本目录 |
| 资源复用 | 4 | 证据规则、替代说明句式、清单模板可直接复用于真实返修 | references/, templates/ |
| 分享价值 | 3 | 四类证据需求映射表与数字溯源判定规则沉淀为显式文档 | evidence_rules.md |
