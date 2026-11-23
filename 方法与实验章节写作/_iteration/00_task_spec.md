# 表 2 · 赛题规格（rubric_source: official_verified）

出处：GET https://play.bohrium.com/api/challenges/product-arena-05-64faa4a2（2026-11-23 复核）与
`playground task download` 的 task.md。以下为原文摘句。

## 任务要求

- "围绕'方法与实验章节写作'制作一个可被 Agent 调用的 Skill，在组织方提供的 3 个固定科研案例上完成实际任务，并交付能够被复核的结果。"
- 四问："写得全／写得准／做得着／说得住"——六类要素：步骤、实验设置、参数、数据集、对照、复现与限制。
- "参赛者只需要选择一个明确方向，形成能够真实运行、独立验证、持续改进的最小成果。"

## 评分维度与权重（照抄，合计 100）

| 维度 | 分值 | 评分点（照抄） |
|-|-|-|
| 实际效果 | 40 | 任务完成度15／结果正确性15／结果完整性5／结果可核验性5 |
| 使用增益 | 25 | 质量增益15／效率增益5／增益可验证性5 |
| 创新增益 | 15 | 新增能力5／方法改进5／创新证据5 |
| 可靠体验 | 10 | 调用与易用性3／运行稳定性4／异常处理3 |
| 生态贡献 | 10 | 文档完整性3／资源可复用性4／分享推广价值3 |

"质量与增益以平台固定案例、基础 Agent/Skill Agent 对照结果和可核验记录为依据；文字自述不能替代实际运行证据。"

## 提交格式与约束（Harbor 技术提交约定，照抄要点）

- "Create /app/submission/SKILL.md and any required text resources. Use valid name/description YAML frontmatter."
- "Do not submit prepared answers or formal test outputs. The evaluator installs the actual Skill under /skills/weekly-skill, then runs official DeepSeek Harness on each fixed original case."
- "original input is /input/case.json and task.md … Work under /app/work; final actual results and editable artifacts belong under /app/output, including result.json with all original output_contract fields and case_id."
- "Include honest status, sources, uncertainty and change records." / "A partial result must identify its limits."
- **"Skill resources: at most 50 UTF-8 text files, 500KB each and 2MB total, no symlinks."** ← v1 批次疑似撞此条
- "Execution budget: 64 model requests, 900 seconds, 16384 tokens per response including reasoning."
- 交付要求含"最小调用示例"与"使用与方法说明"。

## 禁做项（照抄）

- "不能用预制答案代替实际运行" / "do not invent benchmark scores" / "Do not fabricate missing software state or scientific data." / "不依据错误的领域标签补造数据。"

## 评分后端

- scoring.strategy = human_review_only；实测出分为 harbor 三段颗粒（见 02_scoring_model.md 的 N=3 推导）。
