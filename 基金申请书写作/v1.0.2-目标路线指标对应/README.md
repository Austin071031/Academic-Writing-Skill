# grant-alignment-matrix（目标—内容—路线—指标对应）

基金申请书写作 Skill，主攻"对得上"：研究目标、研究内容、技术路线、考核指标四节
逐条对应，不出现目标三个、路线两条、指标另说一套。专属引擎 alignment_engine
机选四节编号条目、建跨节相似度矩阵与编号互引图谱，机检孤儿条目/数量不一致/缺节，
输出 alignment_table.md 对应关系总表；事实台账 + 证据标记 + 材料外事实机检，
交付可直接进入申请书的章节稿与要素对照说明。

- **安装**：本目录即技能根，整体置于 `/skills/weekly-skill` 即可被 Agent 加载；无第三方依赖（Python3 标准库；PDF 解析可选 pdftotext）。
- **快速开始**：按 `SKILL.md` 的 13 步工作流执行；完整说明见 `docs/USAGE.md`；最小示例见 `examples/minimal_example.md`。
- **边界**：不臆造材料外事实；材料缺失如实降级 partial 并登记 manual_confirmations；详见 SKILL.md"限制"。
- **仓库**：https://github.com/Austin071031/Academic-Writing-Skill/tree/main/基金申请书写作/v1.0.2-目标路线指标对应
