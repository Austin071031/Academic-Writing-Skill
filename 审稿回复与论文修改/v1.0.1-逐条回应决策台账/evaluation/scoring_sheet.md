# 评分点-机制对照自查表（v1.0.1 逐条回应决策台账）

| # | 评分点 | 分值 | 本 Skill 对应机制 | 自查方式 |
|-|-|-|-|-|
| 1 | 任务完成度 | 15 | 八步管线交付修订稿+台账生成回复信+定位+证据清单；init_result 骨架防超时空手 | result.json outputs 非空 |
| 2 | 结果正确性 | 15 | 锚点编辑真实落稿；回复信 E# 指涉带真实 status/行号，failed 自动 ⚠；fabrication 拦截编造数字 | verify PASS；信尾问题清单为空 |
| 3 | 结果完整性 | 5 | 回复信由台账装配，意见→子要求全覆盖，缺 disposition 自动标 ⚠【未处置】 | audit letter_structure PASS |
| 4 | 结果可核验性 | 5 | 五重交叉核验 + audit_report.json 四类明细 + 定位行号 + 输入 sha256 入 sources | verification.json 与 audit_report.json overall_pass |
| 5 | 质量增益 | 15 | 台账生成回复信 + 答非所问检测 + 语气审计，为基础 Agent 不具备的结构化能力 | 对照平台白板（漏项/虚报/语气失控） |
| 6 | 效率增益 | 5 | 写信、核对症、扫语气全部脚本化（秒级），Agent 只做复核、决策与润色 | 脚本时间戳 |
| 7 | 增益可验证 | 5 | 同一管线可复跑；generate/audit 确定性输出，产物含全部中间 JSON | work/ 全量保留 |
| 8 | 新增能力 | 5 | 回复信自动装配（E#/EV# 指涉带状态）+ failed op 自动示警 | response_problems.json |
| 9 | 方法改进 | 5 | 答非所问按 action_kind 分类判据；决策-语气一致性强制；四档语气句式库 | references/response_rules.md |
| 10 | 创新证据 | 5 | 合成示例端到端可复跑；含"注入答非所问→audit 检出→修复→PASS"演示 | examples/minimal_example.md |
| 11 | 调用易用 | 3 | SKILL.md 命令逐条可复制；generate/audit 两阶段语义清晰；--file 兜底 | docs/USAGE.md |
| 12 | 运行稳定 | 4 | 纯标准库零依赖；幂等可续跑；可选输入缺失时降级不崩溃 | 重复运行结果一致 |
| 13 | 异常处理 | 3 | 12 类异常处置表（缺材料/锚点失败/failed op 引用/意见有误/手工改信重审…） | SKILL.md 第 4 节 |
| 14 | 文档完整 | 3 | README/USAGE/CHANGELOG/schemas/response_rules/模板/示例齐备 | 本目录 |
| 15 | 资源复用 | 4 | schemas/四档句式库/判据词表/自查表可直接复用到其他返修流程 | references/, templates/ |
| 16 | 分享价值 | 3 | 答非所问判据表与语气红线词表沉淀为显式规则，与引擎同步维护 | response_rules.md 与引擎词表对照 |
