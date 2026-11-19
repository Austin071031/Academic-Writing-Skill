# 评分自查表（grant-alignment-matrix v1.0.2）

按题面评分维度逐项自查；运行后对照真实输出勾选。

## 实际效果（40）

- [ ] 任务完成度：交付物是章节稿＋要素对照说明＋对应矩阵表，不是写作建议/提纲（proposal_draft.md 可直接粘贴）
- [ ] 结果正确性：source_audit high=0；无材料外数字/引用；count_mismatch=0（四节条目数一致）；考核指标全部标〔拟〕
- [ ] 结果完整性：element_mapping.md 要素状态全 ok；研究目标/研究内容/技术路线/考核指标四节齐全（missing_section=0）
- [ ] 结果可核验性：evidence_map 三级对应可回溯；alignment_table.md 逐条展示 目标→内容→路线→指标 对应链

## 使用增益（25）

- [ ] 质量增益：四节无孤儿条目（orphan_*=0 或全部"已驳回"附理由）；alignment_table.md 每个目标行三列均非"—"
- [ ] 效率增益：条目机选/相似度矩阵/对应总表全部脚本秒级完成，Agent 只做设计与写作
- [ ] 增益可验证性：findings 处置前后两轮 audit 输出可比（report.md 分级统计）

## 创新增益（15）

- [ ] 新增能力：四节编号条目机选 + 相似度矩阵/编号互引双判据 + 孤儿/数量不一致/缺节机检（基础 Agent 不具备）
- [ ] 方法改进：seed 写作前条目数自查 + audit 落稿后对应审计的两段式闭环；alignment_table.md 以目标为锚的全链对应视图
- [ ] 创新证据：references/failure_modes.md 七类失败模式与对策一一对应；worked_example 正负例实测命中

## 可靠体验（10）

- [ ] 易用性：SKILL.md 13 步逐字可执行；frontmatter 触发条件明确
- [ ] 稳定性：脚本幂等可重跑；seed 在 draft.json 缺失时优雅降级（打印设计指引 exit 0）
- [ ] 异常处理：异常表 10 类全部有处置路径；材料缺失降级 partial

## 生态贡献（10）

- [ ] 文档完整：SKILL/README/USAGE/3 references/示例/评分表/CHANGELOG
- [ ] 资源可复用：alignment_seed.json、alignment_matrix.json、条目编号体例正则、阈值判据可直接移植
- [ ] 分享价值：worked_example 完整正负例可教学复用
