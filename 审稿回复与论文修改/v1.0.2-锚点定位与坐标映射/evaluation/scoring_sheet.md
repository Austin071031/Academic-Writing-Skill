# 评分点-机制对照自查表（修改定位方向）

| 评分点 | 分值 | 本 Skill 对应机制 | 自查方式 |
|-|-|-|-|
| 任务完成度 | 15 | 八步管线交付修订稿+回复信+定位表+证据清单；init_result 骨架防超时空手 | result.json outputs 非空 |
| 结果正确性 | 15 | 锚点编辑真实落稿；定位坐标由引擎计算而非手抄；fabrication 检查拦截编造数字 | verify PASS；location_table 双坐标完整 |
| 结果完整性 | 5 | 每个 applied op 都有双坐标 + 变更区域挂接；模糊锚/失效锚显式标注 | anchor_map.json dual_coordinates 全覆盖 |
| 结果可核验性 | 5 | **回复信定位声明引擎核验**：E#/引文/坐标逐项对照修订稿，unresolvable_claims 非空即 exit 1；输入文件 sha256 入 sources | anchor_engine exit=0；verification.json overall_pass |
| 质量增益 | 15 | 双坐标定位 + 行级 diff 映射为基础 Agent 不具备的结构化能力 | 对照平台白板 |
| 效率增益 | 5 | 定位表、行号映射、声明核验全部脚本化（秒级），Agent 只做写信与决策 | 脚本时间戳 |
| 增益可验证 | 5 | 同一管线可复跑，anchor_map.json 含全部中间明细 | work/ 全量保留 |
| 新增能力 | 5 | 回复信三类定位声明（E#/引文/坐标）的自动抽取与独立核对 | location_table.md 第 5 节 |
| 方法改进 | 5 | 行级对齐替代手抄行号；锚点四级解析（精确→全局→归一化→模糊）+ 失效标注 | SKILL.md 步骤 6/7 |
| 创新证据 | 5 | 合成示例端到端可复跑；假引文/悬空 E#/越界行号注入检出演示 | examples/minimal_example.md |
| 调用易用 | 3 | SKILL.md 命令逐条可复制；--baseline/--file 兜底 | docs/USAGE.md |
| 运行稳定 | 4 | 纯标准库零依赖；幂等可续跑；基线不可读降级 structure 模式并注明 | 重复运行结果一致 |
| 异常处理 | 3 | 13 类异常处置表（锚点不唯一/模糊锚/失效锚/悬空 E#/引文失配/行号越界/新增段坐标…） | SKILL.md 第 4 节 |
| 文档完整 | 3 | README/USAGE/CHANGELOG/schemas/anchor_rules/模板/示例齐备 | 本目录 |
| 资源复用 | 4 | schemas/模板/定位规则/自查表可直接复用 | references/, templates/ |
| 分享价值 | 3 | 双坐标规范、引文规范、行号映射方法沉淀为显式规则 | anchor_rules.md |
