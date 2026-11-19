# 使用与方法说明（rq-contribution-alignment v1.0.0）

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
| rq_map.json | 主攻维度中间产物：RQ×角色章节覆盖矩阵、贡献×证据三档裁决、首尾呼应矩阵 |
| result.json | 平台契约：case_id + output_contract 全部字段 + status/outputs/evidence_map/change_log/uncertainty/stats |

## 关键方法

- **结构解析**（parse_manuscript.py）：行级标题识别（Markdown `#`、LaTeX `\section`、纯文本的数字编号/中文编号/关键词标题、docx 样式、PDF 文本层），段落空行切分，句子按中英终结符切分，发稳定 ID。
- **六维普查**（six_scan.py）：每维度 ≤8 条候选，保证"结果完整性"评分要求的六类覆盖；未检出维度在报告中显式说明。
- **对齐引擎**（rq_engine.py）：
  - RQ 抽取：提示词正则（研究问题/本文旨在/we aim/RQn…）；
  - 覆盖率：RQ 内容词集合（中文二字组+英文实词）与各角色章节 Jaccard；阈值 `THRESH.rq_cover_overlap=0.20`；
  - 贡献三档：与含数据/图表锚点的结果类段落最大重叠 ≥0.25 supported / ≥0.12 weak / 否则 unsupported；
  - 首尾呼应：摘要+引言论断句 × 结论句 最大 Jaccard，阈值 0.35。

## 适用场景与限制

- 适用：IMRaD 类中英文稿件的投稿前结构自查、导师初审、同行评审前自检。
- 限制：词面重叠方法对同义改写不敏感；非标准文体（综述、观点文）章节角色归类可能失败，此时按平铺处理并下调置信度。所有阈值见 `scripts/scanutil.py:THRESH`。

## 失败处理与自查

- 任一步失败：先读 stderr 的 `[脚本名][issue]` 行；脚本均可独立重跑。
- 交付前自查（对应 evaluation/scoring_sheet.md）：①每条问题能否按位置+锚点指回原文？②六维是否都有结论（含"未检出"说明）？③status 是否与 uncertainty/exceptions 一致？④result.json 是否含 case_id 与全部契约字段？
