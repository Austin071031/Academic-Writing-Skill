# grant-innovation-precision v2.0.3（厚度信息密度）

基金申请书写作 Skill，主攻"说得准+写得够"：创新点写清与具体已有工作的差别，
不依赖 首次/国际领先/填补空白 一类无法核验的修饰；本版在父辈基础上新增
**章节厚度与证据密度机检**——厚度阈值上提（立项依据≥600、技术路线≥450、
研究基础与可行性≥400、其余≥250 字），事实类要素须引用 ≥3 个不同台账事实 FID，
未达标要素自动生成可执行扩展指令（候选 FID + 缺失子点提示）并强制扩写重检，
直至达标或预算兜底如实降级 partial。

- **安装**：本目录即技能根，整体置于 `/skills/weekly-skill` 即可被 Agent 加载；无第三方依赖（Python3 标准库；PDF 解析可选 pdftotext）。
- **快速开始**：按 `SKILL.md` 的 13 步工作流执行；方法判据见 `references/method_rules.md`；标注示例见 `references/worked_example.md`；最小示例见 `examples/minimal_example.md`。
- **边界**：不臆造材料外事实；材料缺失如实降级 partial 并登记 manual_confirmations；详见 SKILL.md"限制"。
- **回归证据**：`regression_report.json`（12/13 脚本与父辈 md5 一致，唯一改动 elements_check.py；合成案例端到端 ALL PASS）。
- **仓库**：https://github.com/Austin071031/Academic-Writing-Skill/tree/main/基金申请书写作/v2.0.3-厚度信息密度
