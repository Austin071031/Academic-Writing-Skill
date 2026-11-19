# 使用与方法说明（paragraph-redundancy-map v1.0.3）

## 调用步骤

1. **环境**：Python ≥ 3.8（纯标准库）；如需解析 PDF，系统需有 `pdftotext`（缺失时按异常表降级，不影响其他格式）。
2. **输入**：`/input/case.json`（含 case_id 与 output_contract）、`/input/task.md`、稿件文件（md/txt/tex/docx/pdf）。多稿件时 `parse_manuscript.py --file <路径>` 指定。
3. **运行**：按 SKILL.md「标准工作流」8 步执行；脚本幂等，中断后重跑继续。
4. **判断**：第 7 步必须人工/Agent 复核草稿——脚本产出候选，误报删除、漏报补登（须带原文锚点）、优先级重排。主攻维度候选重点看"结构性呼应"条目（confidence≤0.6，必须逐条裁决）。
5. **交付**：`validate_output.py` 返回 PASS 方可视为完成；status 必须诚实（success/partial/failed）。

## 输入输出解释

| 产物 | 说明 |
|-|-|
| diagnosis_report.md | 主交付。六维分节；每条问题：ID / 维度 / 类型 / 位置（章节›段落›句子）/ 原文锚点 / 判断依据 / 编辑动作 / 严重度 / 置信度 / 复核状态 |
| edit_plan.json | 机读编辑计划；`ops[]` 与 findings 同 ID，作者逐条执行并勾选采纳/部分采纳/驳回 |
| findings.json | 全部问题的统一 schema，便于二次开发 |
| redundancy_report.json | 主攻维度中间产物：duplicate_pairs / near_duplicate_pairs / structural_echo_pairs / sentence_duplicates / cohesion_gaps / dangling_references / split_candidates / statistics（含 estimated_redundant_chars） |
| result.json | 平台契约：case_id + output_contract 全部字段 + status/outputs/evidence_map/change_log/uncertainty/stats |

## 关键方法

- **结构解析**（parse_manuscript.py）：行级标题识别（Markdown `#`、LaTeX `\section`、纯文本的数字编号/中文编号/关键词标题、docx 样式、PDF 文本层），段落空行切分，句子按中英终结符切分，发稳定 ID。
- **六维普查**（six_scan.py）：每维度 ≤8 条候选，保证"结果完整性"评分要求的六类覆盖；未检出维度在报告中显式说明。
- **主攻引擎**（redundancy.py）：
  - 段落重复对：n_char≥40 段落两两字符 3-gram Jaccard；≥0.55 重复（同章相邻→merge；跨章→删冗余侧+交叉引用；保留启发式：角色核心度 method/experiment/results/discussion > introduction/conclusion > abstract/related_work，平级取先出现者）；0.30–0.55 近似重复（narrow：差异化改写或合并）；
  - 结构性呼应：摘要↔引言、结论↔摘要重叠 ≥0.55 → 单独成表，confidence=0.5 人工裁决；
  - 句子级跨章重复：句子 3-gram ≥0.80 且分属不同章节；
  - 衔接缺失：同章相邻段内容词 Jaccard<0.05 且后段无 CONNECTIVES 开头 → add_transition；回指悬空：段首回指词（如前所述/上文/据此/this shows…）但前 3 段无内容词重叠；
  - 拆分候选：n_char≥400 且内部句子两两平均 terms-Jaccard<0.03，建议拆分点为前后半相似度最低句界；
  - 统计：重复对数、涉及段落数、estimated_redundant_chars（重复对中较短段字符数之和）。
  - findings 上限 15 条，按 重复 > 句子重复 > 呼应 > 近似 > 回指 > 衔接 > 拆分 截断。

## 适用场景与限制

- 适用：IMRaD 类中英文稿件的投稿前查重式自查、篇幅压缩、段落重组；学位论文大章节的重复检测。
- 限制：词面 n-gram 方法对语义级同义复述（完全换词）不敏感；非标准文体（综述、观点文）的"合理复述"密度高，near_duplicate 区间候选误报偏多，须人工裁决。所有阈值见 `scripts/scanutil.py:THRESH` 与 `redundancy_report.json.thresholds`。

## 失败处理与自查

- 任一步失败：先读 stderr 的 `[脚本名][issue]` 行；脚本均可独立重跑。
- 交付前自查（对应 evaluation/scoring_sheet.md）：①每条问题能否按位置+锚点指回原文？②六维是否都有结论（含"未检出"说明）？③"结构性呼应"条目是否逐条人工裁决过？④status 是否与 uncertainty/exceptions 一致？⑤result.json 是否含 case_id 与全部契约字段？⑥statistics.estimated_redundant_chars 与重复对表是否一致？
