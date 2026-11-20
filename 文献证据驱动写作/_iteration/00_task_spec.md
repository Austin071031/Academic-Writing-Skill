# 表 2 赛题规格（task spec）

出处：源 A `https://play.bohrium.com/challenge/challenge-b810ef56`（API 实取，2026-11-20，页面可读、细则含权重）→ `rubric_source: official_verified`。

## 任务要求（原文摘句）

- "你需要围绕"文献证据驱动写作"制作一个可被 Agent 调用的 Skill，在组织方提供的 3 个固定科研案例上完成实际任务，并交付能够被复核的结果。"
- "1. 读取事实底稿、受众、文体和格式约束。2. 完成指定的生成、改写、校对或结构化动作。3. 为事实、数字和引用保留来源或修改记录。4. 对材料不足、冲突和需要人工确认的内容明确标注。"

## 评分维度与权重（原文照抄）

| 维度 | 权重 | 考察内容（原文摘句） |
|-|-|-|
| 实际效果 | **40 分**（任务完成度 15；结果正确性 15；结果完整性 5；结果可核验性 5） | "是否把一段需要文献支撑的写作任务真正落到"论断清单—证据表—成稿"三段交付上"；"引用是否真实存在、是否真的支持该论断"；"论断、来源、证据强度标注、不确定性表述四类要素是否齐备"；"论断编号、原文摘录、定位信息与强度理由能否被独立复核" |
| 使用增益 | **25 分**（质量增益 15；效率增益 5；增益可验证性 5） | "相比不加载的基础 Agent 是否改善证据支撑质量"；"是否减少回原文核对、补引用、改写过度推断段落等人工返工"；"是否通过公平对照证明证据支撑质量的改善" |
| 创新增益 | **15 分**（新增能力 5；方法改进 5；创新证据 5） | "是否形成基础 Agent 或现有方案不具备、或难以稳定实现的论断切分、来源匹配与强度判定能力" |
| 可靠体验 | **10 分**（调用与易用性 3；运行稳定性 4；异常处理 3） | "对文献不可得、仅有摘要、原文与摘要矛盾、证据相互冲突、格式不支持、权限不足等情况的识别与处置能力" |
| 生态贡献 | **10 分**（文档完整性 3；资源可复用性 4；分享推广价值 3） | "使用说明、依赖、配置、示例、适用范围、限制、强度分级口径和维护信息是否齐全" |

- 评分方式（API scoring 字段）：`"strategy": "human_review_only"`，`"formula_summary": "No automated scoring; reviewers grade attempts manually."`
- "质量与增益以平台固定案例、基础 Agent/Skill Agent 对照结果和可核验记录为依据；文字自述不能替代实际运行证据。"

## 提交格式与文件结构（原文摘句）

- "Create /app/submission/SKILL.md and any required text resources. Use valid name/description YAML frontmatter."
- "Skill resources: at most 50 UTF-8 text files, 500KB each and 2MB total, no symlinks."

## 运行契约（原文摘句，Runtime contract 段）

- "The evaluator installs the actual Skill under /skills/weekly-skill, then runs official DeepSeek Harness on each fixed original case."
- "At execution time original input is /input/case.json and task.md."
- "Work under /app/work; final actual results and editable artifacts belong under /app/output, including result.json with all original output_contract fields and case_id."
- "Execution budget: 64 model requests, 900 seconds, 16384 tokens per response including reasoning."
- "实际输入文件和原论文是事实依据；不依据错误的领域标签补造数据。"

## 输出要求（原文摘句）

- "目标产物：可编辑的稿件、改稿、引用/格式结果或结构化写作产物；完成标准：满足题目指定体裁、受众和格式"
- "事实与来源映射：数字、术语、引用、图表和关键论断的来源/修改记录；完成标准：可逐条回溯，不新增材料外事实"
- "版本与边界：修改差异、人工确认项、材料缺口和异常"

## 禁做项（原文摘句）

- "Do not submit prepared answers or formal test outputs."
- "不能用预制答案代替实际运行。"
- "Do not fabricate missing software state or scientific data."
