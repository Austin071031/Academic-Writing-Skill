# 评分点-机制对照自查表

| 评分点 | 分值 | 本 Skill 对应机制 | 自查方式 |
|-|-|-|-|
| 任务完成度 | 15 | 八步管线交付修订稿+回复信+定位+证据清单；init_result 骨架防超时空手 | result.json outputs 非空 |
| 结果正确性 | 15 | 锚点编辑真实落稿；fabrication 检查拦截编造数字；占位不冒充完成 | verify PASS；change_log 逐条 |
| 结果完整性 | 5 | 子要求级覆盖台账（audit 未覆盖即 FAIL） | decomposition_report 第 5 节 |
| 结果可核验性 | 5 | 五重交叉核验 + 定位行号 + 输入文件 sha256 入 sources | verification.json overall_pass |
| 质量增益 | 15 | 拆解/冲突检测/覆盖终检为基础 Agent 不具备的结构化能力 | 对照平台白板 |
| 效率增益 | 5 | 机械劳动脚本化（秒级），Agent 只做复核与决策 | 脚本时间戳 |
| 增益可验证 | 5 | 同一管线可复跑，产物含全部中间 JSON | work/ 全量保留 |
| 新增能力 | 5 | 原子拆解 + 重叠/冲突/依赖检测 | decomposition_report 第 2–4 节 |
| 方法改进 | 5 | 锚点编辑 + 双阶段审计（first/audit） | SKILL.md 步骤 3/7 |
| 创新证据 | 5 | 合成示例端到端可复跑 | examples/minimal_example.md |
| 调用易用 | 3 | SKILL.md 命令逐条可复制；--file 兜底 | docs/USAGE.md |
| 运行稳定 | 4 | 纯标准库零依赖；幂等可续跑；编码自动探测 | 重复运行结果一致 |
| 异常处理 | 3 | 9 类异常处置表（缺材料/锚点失败/冲突/占位…） | SKILL.md 第 4 节 |
| 文档完整 | 3 | README/USAGE/CHANGELOG/schemas/示例齐备 | 本目录 |
| 资源复用 | 4 | schemas/模板/词表/自查表可直接复用 | references/, templates/ |
| 分享价值 | 3 | 拆解判据与冲突词表沉淀为显式规则 | decomposition_rules.md |
