# grant-innovation-precision（创新点差异定位）

基金申请书写作 Skill，主攻"说得准"：创新点写清与具体已有工作的差别，
不依赖 首次/国际领先/填补空白 一类无法核验的修饰；事实台账 + 证据标记 +
材料外事实机检，交付可直接进入申请书的七要素章节稿与要素对照说明。

- **安装**：本目录即技能根，整体置于 `/skills/weekly-skill` 即可被 Agent 加载；无第三方依赖（Python3 标准库；PDF 解析可选 pdftotext）。
- **快速开始**：按 `SKILL.md` 的标准工作流执行；最小示例见 `examples/minimal_example.md`。
- **本版（v2.0.2-契约自动对齐）**：在父辈 v1.0.3 基础上新增契约自动对齐——`scripts/contract_check.py` 将 case.json 的 output_contract 逐字段语义映射到实际产物并机检存在性（`work/contract_map.json`），assemble_result 回填每字段产物路径与中文说明；其余资产与父辈一致。
- **边界**：不臆造材料外事实；材料缺失如实降级 partial 并登记 manual_confirmations；详见 SKILL.md"限制"。
- **仓库**：https://github.com/Austin071031/Academic-Writing-Skill/tree/main/基金申请书写作/v2.0.2-契约自动对齐
