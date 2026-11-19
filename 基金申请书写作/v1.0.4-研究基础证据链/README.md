# grant-feasibility-evidence（研究基础证据链）

基金申请书写作 Skill，主攻"研究基础·查得到"：把散落的前期成果、平台条件、团队分工
组织成**能力—证据—与本研究关系**三列证据链，引用的成果逐条追溯到具体来源（〔F〕锚定台账），
并用体貌机检严格区分已完成与拟开展。交付可直接进入申请书的七要素章节稿与要素对照说明。

- **安装**：本目录即技能根，整体置于 `/skills/weekly-skill` 即可被 Agent 加载；无第三方依赖（Python3 标准库；PDF 解析可选 pdftotext）。
- **快速开始**：按 `SKILL.md` 的 13 步工作流执行；完整说明见 `docs/USAGE.md`；最小示例见 `examples/minimal_example.md`。
- **专属引擎**：`scripts/feasibility_engine.py seed|audit`——seed 机选证据链行（`work/evidence_chain_seed.json`），audit 审计体貌冲突/成果无锚定/证据链缺列/可行性缺失（`work/findings.json`）。
- **边界**：不臆造材料外事实；材料缺失如实降级 partial 并登记 manual_confirmations；详见 SKILL.md"限制"。
- **仓库**：https://github.com/Austin071031/Academic-Writing-Skill/tree/main/基金申请书写作/v1.0.4-研究基础证据链
