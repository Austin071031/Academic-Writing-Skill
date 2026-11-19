# 评分自查表（grant-rationale-chain v1.0.0）

按题面评分维度逐项自查；运行后对照真实输出勾选。

## 实际效果（40）

- [ ] 任务完成度：交付物是章节稿＋要素对照说明，不是写作建议/提纲（proposal_draft.md 可直接粘贴）
- [ ] 结果正确性：source_audit high=0；无材料外数字/引用；已完成与拟开展分清（〔拟〕标记）
- [ ] 结果完整性：element_mapping.md 七要素状态全 ok，厚度达 inspection/workorder 要求
- [ ] 结果可核验性：evidence_map 三级对应（段落→要素→证据 FID→来源坐标）可逐条回溯

## 使用增益（25）

- [ ] 质量增益：论证链三段齐备、口号零命中（findings.json 为证）
- [ ] 效率增益：槽位候选/台账/审计全部脚本秒级完成，Agent 只做审定与写作
- [ ] 增益可验证性：findings 处置前后两轮审计输出可比（report.md 分级统计）

## 创新增益（15）

- [ ] 新增能力：三段论证链槽位机选 + 口号/锚定/缺环机检（基础 Agent 不具备）
- [ ] 方法改进：证据标记语法 + 事实台账 + 材料外事实审计闭环
- [ ] 创新证据：references/failure_modes.md 六类失败模式与对策一一对应

## 可靠体验（10）

- [ ] 易用性：SKILL.md 13 步逐字可执行；frontmatter 触发条件明确
- [ ] 稳定性：脚本幂等可重跑；骨架先行防超时空手
- [ ] 异常处理：异常表 8 类全部有处置路径；材料缺失降级 partial

## 生态贡献（10）

- [ ] 文档完整：SKILL/README/USAGE/3 references/示例/评分表/CHANGELOG
- [ ] 资源可复用：rationale_chain.json、口号词表、改写句式、证据标记语法可直接移植
- [ ] 分享价值：worked_example 完整标注示例可教学复用
