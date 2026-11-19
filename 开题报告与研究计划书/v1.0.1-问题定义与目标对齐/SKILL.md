---
name: proposal-question-objective-aligner
description: 将宽泛研究方向收敛为 1—3 个可证伪的研究问题，并为每个问题生成可考核目标（指标、阈值及依据、样本、对照、时间点），再用追踪矩阵强制“问题—目标—技术路线—里程碑—预期成果”逐行对齐。适用于开题报告、研究计划书中问题定义与目标设定薄弱、各章节各写各的、指标阈值无依据的任务；输出对齐矩阵与全要素可编辑稿件。
---

# 开题报告：问题定义与目标对齐（Question–Objective Alignment）

## 用途与适用边界

开题评审最常见的扣分点是“目标、技术路线、验证方式与预期成果各写各的”。本 Skill 以**对齐追踪矩阵**为主工件：先收敛问题，再为每个问题定义可考核目标，随后所有章节必须能逐行挂到矩阵上，挂不上的内容即判定为漂移并删除或改写。

适用：给定材料需产出/修改开题报告、研究计划书、课题论证的任务。
不适用：无任何输入材料的自由命题；此时按异常处理索要材料或显式标注假设。

## 运行契约（评测环境必读）

1. 读取 `/input/case.json` 与 `/input/task.md`，以其为唯一事实来源；**禁止补造材料外数据、引用与结论**；PDF 等材料解析实际文本。
2. 中间产物写 `/app/work`；最终产物写 `/app/output`。
3. `/app/output/result.json` 逐字段包含 `output_contract` 全部键 + `case_id`、`status`、`artifacts`、`sources`、`uncertainty`、`change_log`。
4. 交付 `proposal.md`/`proposal.docx`，并用 `scripts/build_output.py` 渲染真实 PDF 与首页 PNG；失败降级 `partial` 并记录，不伪造。
5. 缺失/冲突/待确认内容写入稿件第 10 章与 `uncertainty`，不静默假设。
6. 预算 64 次请求、900 秒：先存完整初稿再迭代。

## 工作流程

### 第 1 步：候选问题生成与收敛
从材料中提取全部可能的研究切入点，按三问过滤收敛到 1—3 个研究问题：
- 可回答吗？——在材料给定的数据、周期、经费条件下能产出答案。
- 可证伪吗？——能写出“若 X 则支持、若 Y 则否定”的判据。
- 值得做吗？——指向材料中明示的缺口或需求。
每个问题写入否定判据。收敛过程与被淘汰的候选记入 `change_log`。

### 第 2 步：假设—检验矩阵（目标设定）
对每个问题 Qi 建立条目（模板 `templates/question_objective_matrix.md`）：
- 假设 Hi、验证方式；
- **指标**（度量名）、**阈值**（判定线）及**依据**——依据只能来自材料/文献；无依据的阈值标注“假设值，待导师确认”；
- 样本、对照、时间点（时间轴以 case.json 给定周期为界）。

### 第 3 步：构建对齐追踪矩阵
以问题为行，逐行挂接：目标 ↔ 路线步骤 ↔ 里程碑 ↔ 预期成果 ↔ 考核方式（模板 `templates/traceability_matrix.md`）。规则：每行至少一个非空单元；任何章节内容挂不上行即为漂移，删除或改写；目标数与问题数一致。

### 第 4 步：撰写全稿
按 `templates/proposal_template.md` 写七要素。背景仍须“已知—未知—待验证”且不罗列文献；阶段计划落在给定周期经费内；风险含触发信号/备选/决策时点；引用 [n] 与参考文献一一对应。

### 第 5 步：对齐自检与交付
```bash
python3 scripts/validate_proposal.py /app/work/proposal.md --profile objective --report /app/output/validation_report.json
python3 scripts/build_output.py --work /app/work --out /app/output --case /input/case.json
```
重点核对：问题数=目标数；每个目标四要素（指标/阈值/样本对照/时间点）齐全；矩阵每行闭合。

## 输出契约

同通用契约：可编辑稿件 + 真实渲染预览 + `result.json`（output_contract 全字段）+ `validation_report.json`。对齐矩阵作为稿件一章（“问题—目标—路线—成果对齐矩阵”）保留在可编辑稿件中，便于导师逐行审改。

## 异常处理

- **材料无阈值依据**：阈值写为“假设值（依据待补）”并列入人工确认项，不得编造文献支撑。
- **问题在给定条件下不可回答**：缩小问题范围（限定样本/场景/指标）并记录修改理由；仍不可行则 status=partial。
- **目标被要求增加但无法考核**：拒绝写入，说明理由；可考核性是硬约束。
- **周期/经费与目标冲突**：按矩阵回退——优先保留可考核的核心目标，降级或删除不可达目标，记录取舍。
- **学科规范冲突**（如对照设置与伦理要求矛盾）：并列说明，列入人工确认。

## 资源文件

- `templates/question_objective_matrix.md`、`templates/traceability_matrix.md`、`templates/proposal_template.md`
- `checklists/quality_checklist.md`（B 组“对得上”为重点核查项）
- `scripts/validate_proposal.py --profile objective`、`scripts/build_output.py`

## 最小调用示例（示意）

`case.json` 给定周期 24 个月、经费 30 万、前期数据集 D。输出 `result.json` 含 output_contract 字段、`artifacts` 列表、`sources`（材料位置与 [n] 文献）、`uncertainty`（如无阈值依据的假设值清单）。对齐矩阵以 Markdown 表存于稿件第 4 章。
