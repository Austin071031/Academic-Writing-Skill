# 评分自查表（grant-feasibility-evidence v1.0.4）

按题面评分维度逐项自查；运行后对照真实输出勾选。

## 实际效果（40）

- [ ] 任务完成度：交付物是章节稿＋要素对照说明，不是写作建议/提纲（proposal_draft.md 可直接粘贴）
- [ ] 结果正确性：source_audit high=0；无材料外数字/引用；研究基础节已完成/拟开展体貌分清
      （findings.json 无 aspect_violation / unsourced_achievement 未处置项）
- [ ] 结果完整性：element_mapping.md 七要素状态全 ok，研究基础节厚度达标且含可行性论证
- [ ] 结果可核验性：evidence_map 三级对应可回溯；研究基础节成果断言逐条〔F〕锚定台账来源坐标

## 使用增益（25）

- [ ] 质量增益：证据链三列齐备（evidence_chain.json 每行 relation_to_project 非空）、
      体貌冲突零命中（findings.json 为证）
- [ ] 效率增益：证据链行机选/台账/审计全部脚本秒级完成，Agent 只做审定与写作
- [ ] 增益可验证性：findings 处置前后两轮审计输出可比（report.md 分级统计）

## 创新增益（15）

- [ ] 新增能力：能力—证据—关系三列证据链机选 + 体貌冲突/成果无锚定机检（基础 Agent 不具备）
- [ ] 方法改进：aspect_classify 体貌信号 + 成果类〔F〕（type×角色双限定）+ 证据标记语法闭环
- [ ] 创新证据：references/failure_modes.md 六类失败模式与对策一一对应

## 可靠体验（10）

- [ ] 易用性：SKILL.md 13 步逐字可执行；frontmatter 触发条件明确
- [ ] 稳定性：脚本幂等可重跑；seed 与审定版分离（seed 永不被 Agent 覆盖）；骨架先行防超时空手
- [ ] 异常处理：异常表 10 类全部有处置路径；材料缺失降级 partial

## 生态贡献（10）

- [ ] 文档完整：SKILL/README/USAGE/3 references/示例/评分表/CHANGELOG
- [ ] 资源可复用：evidence_chain.json 三列模式、体貌词表、成果断言锚定规则可直接移植
- [ ] 分享价值：worked_example 完整标注示例（含反例命中表）可教学复用
