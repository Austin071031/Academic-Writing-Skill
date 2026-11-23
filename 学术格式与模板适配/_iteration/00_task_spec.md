# 表 2 · 赛题规格（challenge-96263d10）

出处：`https://play.bohrium.com/api/challenges/challenge-96263d10`（2026-11-23 重采，与 11-19 一致）
`rubric_source: official_verified`（页面可读，细则含维度名+分值+考察内容）

## 评分维度（逐行照抄，权重=分值原样）

| 维度 | 分值 | 考察内容（原文摘句） |
|-|-|-|
| 实际效果 | 40 | "是否真正把一份真实稿件按目标模板改到可交付，而不是只改了几处看得见的格式"；"格式规格与内容是否同时正确——字号、行距、页边距、栏数、题注位置、参考文献样式是否符合目标模板，同时正文、图表、公式、引用、批注是否被错误改动"；"模板要求的检查项与原稿的内容单元是否都被覆盖"；"他人能否按提交材料复现'从输入件到成品'的过程并核对每一项"（评分点：任务完成度15/结果正确性15/结果完整性5/结果可核验性5） |
| 使用增益 | 25 | "在相同输入稿件、相同目标模板、相同工具权限下，加载 Skill…相比不加载的基础 Agent 是否提升适配质量"；"是否减少逐项核对、重复排版、试错导出与人工返工"；"是否通过公平对照证明质量或效率改善"（质量增益15/效率增益5/增益可验证性5） |
| 创新增益 | 15 | "是否形成基础 Agent 或现有排版工具不具备、或难以稳定实现的能力，例如从模板文件反推检查项清单、图表题注与交叉引用联动更新、转换后自动比对保真度"（新增能力5/方法改进5/创新证据5） |
| 可靠体验 | 10 | "Agent 是否能正确触发和调用"；"在不同模板类型、不同稿件长度、不同运行环境和重复运行下能否持续产出可用文件"；"对模板缺失或版本不明、字体缺失、样式冲突、转换失败、内容无法保真等情况的识别与处置能力"（调用易用性3/运行稳定性4/异常处理3） |
| 生态贡献 | 10 | "使用说明、依赖环境、支持模板范围、示例、限制与维护信息是否齐全"；"检查项清单、样式映射脚本、样例输入输出能否被他人复用"（文档3/可复用4/分享价值3） |

## 交付要求（原文摘句）

- "参赛者只提交 Skill 及其必要资源；平台统一使用本题固定的 3 个案例运行 Skill"
- Skill 本体：`SKILL.md` + "实际使用的提示、规则或处理流程；写清用途、适用条件、调用方式、输入输出和异常处理"；"不能用预制答案代替实际运行"
- 输出："每个案例返回一份结构化结果，保留输入标识、主结果、证据/来源定位、运行状态和不确定性"；产物"满足题目指定体裁、受众和格式"；"可逐条回溯，不新增材料外事实"；"结果可继续编辑，未确认部分明确标注"

## Runtime contract（原文摘句）

- "Create /app/submission/SKILL.md… The evaluator installs the actual Skill under /skills/weekly-skill, then runs official DeepSeek Harness on each fixed original case."
- "At execution time original input is /input/case.json and task.md… Work under /app/work; final actual results and editable artifacts belong under /app/output, including result.json with all original output_contract fields and case_id."
- "Editable Office/slide/diagram outputs should also have real rendered PDF/PNG previews for inspection."
- "Execution budget: 64 model requests, 900 seconds, 16384 tokens per response including reasoning. Save honest partial deliverables early and improve incrementally."
- "Skill resources: at most 50 UTF-8 text files, 500KB each and 2MB total, no symlinks."
- "Organizer template font revision3: use supplied Liberation Serif"

## 禁做项

- "不依据错误的领域标签补造数据"；不提交预制答案；不伪造软件状态或科学数据；不发明 benchmark 分数。
