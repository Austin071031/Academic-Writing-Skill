# 使用与方法说明（section-narrative-flow v2.0.4）

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
| section_map.json | 主攻维度中间产物：角色序列表（含逆序对）、篇幅占比表、缩写首现表、`xref_audit` 交叉引用审计（引用侧/定义侧统计、悬空清单、未引用条目、skipped 说明、method_note） |
| restructured_outline.md | 重组大纲草稿：现状序列 → 建议叙事顺序（各节去向 + 动作汇总） |
| result.json | 平台契约：case_id + output_contract 全部字段 + status/outputs/evidence_map/change_log/uncertainty/stats |

## 关键方法

- **结构解析**（parse_manuscript.py）：行级标题识别（Markdown `#`、LaTeX `\section`、纯文本的数字编号/中文编号/关键词标题、docx 样式、PDF 文本层），段落空行切分，句子按中英终结符切分，发稳定 ID。
- **六维普查**（six_scan.py）：每维度 ≤8 条候选，保证"结果完整性"评分要求的六类覆盖；未检出维度在报告中显式说明。
- **章节流引擎**（section_flow.py）：
  - 角色归类：标题关键词 → 12 类角色（`ROLE_MAP`）；正文占比 = 章节字符 / 非后置章节总字符。
  - 逆序对：角色序列表与 `CANONICAL_ORDER`（摘要→…→参考文献→附录）两两比对，后者规范序低于前者即一条 move 候选。
  - 篇幅阈值：`THRESH.section_imbalance=0.55`（拆分）、方法 <8% 且存在结果章（方法过薄）、引言 >35%（铺垫过长）。
  - 层级与空章：相邻标题层级差 >1（跳变）、同级同名标题（合并候选）、n_para=0（空章）。
  - 缩写首现：正则 `[A-Z][A-Z0-9]{1,7}s?` 抽取；在首现句及相邻句查"全称（ABBR）/ ABBR（全称）"定义模式，未命中即"信息过早释放"。
  - 回指悬空："如前所述/aforementioned"句与前 200 词内容词重叠 ≈0 → add_transition 候选。
  - 方法泄漏：结果/讨论/结论章段落含 ≥2 句方法性描述（采用/步骤/配置为…）→ 后移方法章候选。
  - **交叉引用完整性审计（v2.0.4，dimension=argument_chain）**：图/表/公式/章节/文献编号的引用侧（正文句子正则提取）与定义侧（独立图注段/段末公式编号/标题数字编号/文献条目）双向核对。引用编号无定义 → 悬空（high，"补定义或修正编号"）；[1..n] 文献条目未被正文引用 → medium（"删除或在正文补引"）；被引图表编号跳号（无悬空时）→ low 提示。无参考文献表或标题无数字编号时对应项自动跳过（记入 `xref_audit.skipped`，防误报）。每类上限 3 条，与原有 findings 合并后按 severity 稳定截断 ≤15。判据细节见 references/structure_rules.md 第 8 节。

## 适用场景与限制

- 适用：IMRaD 类中英文稿件的投稿前结构自查、导师初审、同行评审前自检、章节重组编辑。
- 限制：词面/标题关键词方法对同义改写与刁钻标题不敏感；非标准文体（综述、观点文）序列判定置信度下降。所有阈值见 `scripts/scanutil.py:THRESH`。

## 失败处理与自查

- 任一步失败：先读 stderr 的 `[脚本名][issue]` 行；脚本均可独立重跑。
- 交付前自查（对应 evaluation/scoring_sheet.md）：①每条问题能否按位置+锚点指回原文？②六维是否都有结论（含"未检出"说明）？③status 是否与 uncertainty/exceptions 一致？④result.json 是否含 case_id 与全部契约字段？⑤section_map.json 与 restructured_outline.md 是否生成且与报告一致？⑥xref_audit 的悬空清单是否逐条经第 7 步裁决（图注不在文本层、支撑材料编号、文献表分节等误报源见 references/failure_modes.md）？
