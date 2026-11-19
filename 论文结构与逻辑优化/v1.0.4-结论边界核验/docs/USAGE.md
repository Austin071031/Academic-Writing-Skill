# 使用与方法说明（conclusion-boundary-check v1.0.4）

## 调用步骤

1. **环境**：Python ≥ 3.8（纯标准库）；如需解析 PDF，系统需有 `pdftotext`（缺失时按异常表降级，不影响其他格式）。
2. **输入**：`/input/case.json`（含 case_id 与 output_contract）、`/input/task.md`、稿件文件（md/txt/tex/docx/pdf）。多稿件时 `parse_manuscript.py --file <路径>` 指定。
3. **运行**：按 SKILL.md「标准工作流」8 步执行；脚本幂等，中断后重跑继续。
4. **判断**：第 7 步必须人工/Agent 复核草稿——脚本产出候选，误报删除、漏报补登（须带原文锚点）、优先级重排。
5. **交付**：`validate_output.py` 返回 PASS 方可视为完成；status 必须诚实（success/partial/failed）。

## 输入输出解释

| 产物 | 说明 |
|-|-|
| diagnosis_report.md | 主交付。六维分节；每条问题：ID / 维度 / 类型 / 位置（章节›段落›句子）/ 原文锚点 / 判断依据 / 编辑动作 / 严重度 / 置信度 / 复核状态 |
| edit_plan.json | 机读编辑计划；`ops[]` 与 findings 同 ID，作者逐条执行并勾选采纳/部分采纳/驳回 |
| findings.json | 全部问题的统一 schema，便于二次开发 |
| boundary_audit.json | 主攻维度中间产物：数字溯源表（逐条 verdict+匹配源+相对差）、摘要-结论一致性表、因果三档表、范围比对表、限制审计 |
| result.json | 平台契约：case_id + output_contract 全部字段 + status/outputs/evidence_map/change_log/uncertainty/stats |

## 关键方法

- **结构解析**（parse_manuscript.py）：行级标题识别（Markdown `#`、LaTeX `\section`、纯文本的数字编号/中文编号/关键词标题、docx 样式、PDF 文本层），段落空行切分，句子按中英终结符切分，发稳定 ID。
- **六维普查**（six_scan.py）：每维度 ≤8 条候选，保证"结果完整性"评分要求的六类覆盖；未检出维度在报告中显式说明。
- **边界核验引擎**（boundary_audit.py），目标句 = 摘要/结论全部句 + 讨论章末段：
  - 数字溯源三层匹配：逐字命中 → 等值换算（%×100）→ 相对差 ≤5% 且舍入一致 → 无源数字；源章 = 方法/实验/结果/讨论；年份（19xx/20xx）与图表/公式/章节编号不计入；
  - 摘要-结论一致性：句对内容词 Jaccard ≥0.4 视为同语境，数字集合（含 %×100 等值换算）不一致即报；
  - 因果三档：结论/摘要因果句 → 方法实验章有设计词 supported / 正文仅相关性词 overreach / 皆无 unverifiable；
  - 推广超界：范围词（所有体系/任何/通用/universal…）× 方法实验章枚举的体系/材料/数据集线索；
  - 限制审计：missing / misplaced（致谢附录）/ insufficient（一句无量化）/ adequate 四态。

## 适用场景与限制

- 适用：IMRaD 类中英文稿件的投稿前结论自查、导师初审、同行评审前自检。
- 限制：数字溯源是词面+数值比对，不识别语义出处（被引文献数据、常识常数）；因果三档依赖设计词命中，非常规措辞判 unverifiable；平铺无标题文本角色归类失败时按降级路径处理并下调置信度。

## 失败处理与自查

- 任一步失败：先读 stderr 的 `[脚本名][issue]` 行；脚本均可独立重跑。
- 交付前自查（对应 evaluation/scoring_sheet.md）：①每条问题能否按位置+锚点指回原文？②boundary_audit.json 每张表的 verdict 是否逐条经得起复核？③六维是否都有结论（含"未检出"说明）？④status 是否与 uncertainty/exceptions 一致？⑤result.json 是否含 case_id 与全部契约字段？
