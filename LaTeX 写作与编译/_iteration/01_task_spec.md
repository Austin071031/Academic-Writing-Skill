# 表 2 · 赛题规格（写作13｜LaTeX 写作与编译）

出处：赛题 API `https://play.bohrium.com/api/challenges/product-arena-07-865de7e4`
（公开可读，2026-11-23 复核，存档 challenge-13/challenge.json）。
rubric_source: **official_verified**（题面原文经公开 API 取得；§0-11 填"否"指未拿到
内部详细分档，故维度→机制的拆解映射仍标 self_mapping_unverified）。

## 任务要求（原文摘句）

- "你需要围绕'LaTeX 写作与编译'制作一个可被 Agent 调用的 Skill，在组织方提供的 3 个固定
  科研案例上完成实际任务，并交付能够被复核的结果。"
- 四个关注点："**编译得通**：源码在指定模板与 TeX 发行版下能否按预期轮次编译通过，报错能否
  定位到具体文件、行号与根因，而不是停在第一条错误信息上。**改得对**：公式符号与编号、
  表格数值与列宽、交叉引用与参考文献、版式与模板必填项，是否既符合原文意图又符合模板要求。
  **交得可用**：交付物是否为结构清楚、可继续编辑和维护的源码……**复现得了**：他人按记录中的
  模板版本、宏包与字体版本、编译命令与轮次，能否得到同一份产物。"
- "材料缺失、无法判断和运行失败要分别说明。"

## 评分维度与权重（原文照抄）

| 维度 | 分值 | 评分点 | 考察内容（摘句） |
|-|-|-|-|
| 实际效果 | 40 | 任务完成度15；结果正确性15；结果完整性5；结果可核验性5 | "是否真正交付了能在指定模板下编译通过、并可并入稿件的 .tex 成果"；"编译产物中的公式、表格、引用与版式是否与原文意图及模板要求一致"；"任务要求的改动点、模板必填项与配套文件是否逐项覆盖"；"源码改动、编译过程和产物是否能被独立复核" |
| 使用增益 | 25 | 质量增益15；效率增益5；增益可验证性5 | "加载 Skill 后，相比不加载的基础 Agent 是否提升编译成功率与修复正确率"；"是否减少定位报错、查宏包文档、反复编译和人工核对的成本"；"是否通过公平对照证明质量或效率改善" |
| 创新增益 | 15 | 新增能力5；方法改进5；创新证据5 | "基础 Agent 或现有方案不具备、或难以稳定实现的能力"；"错误分类、修复策略、编译验证闭环等方法是否带来实质改进"；"是否证明创新点相对已有方案的边界和价值" |
| 可靠体验 | 10 | 调用与易用性3；运行稳定性4；异常处理3 | "在不同模板、不同 TeX 发行版和重复运行下能否持续产出可编译且一致的源码"；"对缺宏包、缺字体、报错级联、模板类文件缺失、权限不足等情况的识别与处置能力" |
| 生态贡献 | 10 | 文档完整性3；资源可复用性4；分享推广价值3 | "使用说明、环境依赖、配置、示例、适用范围、限制和维护信息是否齐全"；"Skill 本体、脚本、示例工程、检查清单和评分表能否被他人复用" |

另："质量与增益以平台固定案例、基础 Agent/Skill Agent 对照结果和可核验记录为依据；
文字自述不能替代实际运行证据。"

## 提交格式与文件结构（Harbor 契约，原文摘句）

- "Create /app/submission/SKILL.md and any required text resources. Use valid name/description
  YAML frontmatter. Do not submit prepared answers or formal test outputs."
- "The evaluator installs the actual Skill under /skills/weekly-skill, then runs official
  DeepSeek Harness on each fixed original case."
- "At execution time original input is /input/case.json and task.md … PDF parsing receives the
  actual PDF without a pre-extracted answer layer. … Work under /app/work; final actual results
  and editable artifacts belong under /app/output, including result.json with all original
  output_contract fields and case_id. Include honest status, sources, uncertainty and change
  records. Editable Office/slide/diagram outputs should also have real rendered PDF/PNG previews
  for inspection. A partial result must identify its limits."

## 预算与依赖限制（原文摘句）

- "Execution budget: 64 model requests, 900 seconds, 16384 tokens per response including
  reasoning. Save honest partial deliverables early and improve incrementally."
- "Three cases, three repetitions per condition."
- "Skill resources: at most 50 UTF-8 text files, 500KB each and 2MB total, no symlinks."

## 明确禁做项（原文摘句）

- "Do not submit prepared answers or formal test outputs."
- "do not invent benchmark scores."
- "Do not fabricate missing software state or scientific data."
- "不依据错误的领域标签补造数据。"

## 评分方式

- `"strategy": "human_review_only"`，`"formula_summary": "No automated scoring; reviewers
  grade attempts manually."`；实测 harbor 机器分先行（scorecard.harbor_score）。
