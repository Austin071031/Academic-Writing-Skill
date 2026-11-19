# 使用与方法说明（argument-chain-audit v1.0.2）

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
| chain_audit.json | 主攻维度中间产物：论断总数与分档统计、逐条论断—论据映射表（类型/支撑档/各层锚点明细） |
| result.json | 平台契约：case_id + output_contract 全部字段 + status/outputs/evidence_map/change_log/uncertainty/stats |

## 关键方法

- **结构解析**（parse_manuscript.py）：行级标题识别（Markdown `#`、LaTeX `\section`、纯文本的数字编号/中文编号/关键词标题、docx 样式、PDF 文本层），段落空行切分，句子按中英终结符切分，发稳定 ID。
- **六维普查**（six_scan.py）：每维度 ≤8 条候选，保证"结果完整性"评分要求的六类覆盖；未检出维度在报告中显式说明。
- **论证链引擎**（chain_audit.py）：
  - 论断抽取：`CLAIM_CUES` 正则逐句命中；按线索词分类——比较（优于/超过/higher than/显著）、因果（`CAUSAL_CUES`）、概括（表明/说明/可见/indicate）、绝对（`ABSOLUTE_CUES`）；
  - 论据锚点：引用（`EVIDENCE_CITES`）、图表/公式/章节交叉引用（`EVIDENCE_FIGTAB`）、带单位数字（`EVIDENCE_NUMBER`）；
  - 支撑分档：同句或同段有锚点 → strong；相邻段（±1）有锚点 → weak；窗口内无锚点 → none（断裂，high）；
  - 逻辑跳跃：论断句内容词在其前 3 段从未出现（新词比例 ≥0.6 且 ≥4 个、无论据）→ add_transition；
  - 循环论证近似：两条论断 3-gram Jaccard ≥0.7 且两处都无锚点 → medium、confidence≤0.6、注明需人工确认；
  - 强度不足：因果/绝对论断所在段落无 `DESIGN_CUES`（对照/消融/基线/随机），且只有相关性词或单点数据 → qualify（high）；
  - 比较无对象：显性比较词（优于/超过/better than…）句中无 [n] 引用、无拉丁字母专名、无"基线/baseline" → medium。

## 适用场景与限制

- 适用：IMRaD 类中英文稿件的投稿前论证自查、导师初审、同行评审前自检。
- 限制：锚点检测是词面的——无单位数字（"提升约一倍"）、口语化图表指代（"上图"）、段末统一标注引用等写法会漏检，产生假"断裂"；循环论证为 3-gram 相似近似判定，结论复述摘要可能命中。所有阈值见 `scripts/scanutil.py:THRESH` 与 `scripts/chain_audit.py:TH`。

## 失败处理与自查

- 任一步失败：先读 stderr 的 `[脚本名][issue]` 行；脚本均可独立重跑。
- 交付前自查（对应 evaluation/scoring_sheet.md）：①每条问题能否按位置+锚点指回原文？②六维是否都有结论（含"未检出"说明）？③chain_audit.json 分档统计与明细是否一致？④status 是否与 uncertainty/exceptions 一致？⑤result.json 是否含 case_id 与全部契约字段？
