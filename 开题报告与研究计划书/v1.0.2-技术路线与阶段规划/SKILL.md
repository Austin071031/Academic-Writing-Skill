---
name: proposal-roadmap-planner
description: 将技术路线拆解为带输入/输出/依赖的步骤序列，映射到按给定周期排布的里程碑，并做资源可行性核算（工时、经费、数据、人员）。适用于开题报告、研究计划书中阶段计划排不进周期、里程碑与任务量不匹配、经费超支等可行性问题；输出含关键路径、甘特图与资源核算表的可编辑稿件。
---

# 开题报告：技术路线与阶段规划（Feasible Roadmap Planning）

## 用途与适用边界

本 Skill 把“排得开”变成可计算问题：步骤依赖图 → 关键路径 → 周期/经费/人力核算 → 里程碑验收表。计划若不可行，如实暴露矛盾并给出可行化方案，而不是写一份装得下的假计划。

适用：给定周期、经费、数据与人员条件，需产出或修改开题报告/研究计划书的任务。
不适用：无条件约束的自由写作；此时索要约束或按异常处理显式假设。

## 运行契约（评测环境必读）

1. 读取 `/input/case.json` 与 `/input/task.md` 为唯一事实来源；**禁止补造材料外数据**；PDF 解析实际文本。
2. 中间产物 `/app/work`；最终产物 `/app/output`。
3. `result.json` 逐字段含 `output_contract` 全部键 + `case_id`、`status`、`artifacts`、`sources`、`uncertainty`、`change_log`。
4. 交付 `proposal.md`/`proposal.docx`，`scripts/build_output.py` 渲染真实 PDF/首页 PNG；失败降级 `partial` 不伪造。
5. 缺口与冲突写入稿件第 10 章与 `uncertainty`。
6. 预算 64 请求、900 秒：先存完整初稿再迭代。

## 工作流程

### 第 1 步：路线拆解（步骤表）
把研究方案拆成步骤 S1…Sn（模板 `templates/route_steps.md`），每步必填：内容、输入、输出、前置依赖、预估工时（人月或人周）、所需资源（设备/数据/经费科目）、可否并行。步骤必须与研究目标对应（引用 V2 对齐矩阵的对应关系；若目标未先行定义，先按模板补出 1—3 个目标再拆解）。

### 第 2 步：依赖排序与关键路径
由前置依赖列构造依赖图，拓扑排序后标注**关键路径**（总工时最长的链）与可并行段。无法排序（出现环或缺失前置）时在 uncertainty 中报告并人工假设一个可行顺序。

### 第 3 步：资源可行性核算
以 case.json 给定的周期 T、经费 B、人员 P 为硬约束逐项核算（写入 `templates/resource_check.md` 表）：
- 工时：Σ步骤工时 ≤ P×T（含 20% 缓冲；缓冲比例无依据时标注为经验假设）；
- 关键路径时长 ≤ T；
- 经费：各科目合计 ≤ B，每条支出挂到步骤；
- 数据与人员：所需数据集、技能逐项核对材料条件，缺失项标注。
任一不满足 → 进入第 4 步可行化处理，并在稿件中如实呈现“约束—矛盾—调整”。

### 第 4 步：可行化与里程碑映射
调整手段优先级：并行化 → 裁剪非关键目标 → 降级指标 → 申请追加资源（列入人工确认）。将可行后的步骤映射到按季度/月的里程碑 M1…Mn（模板 `templates/milestones.md`），每个里程碑含时间点、交付物、验收标准，且时间点覆盖整条时间轴、落在 T 内。同时生成 `/app/work/milestones.json`（`[{"id","label","start_month","end_month"}]`），`build_output.py` 会自动渲染 `gantt.png` 甘特图预览。

### 第 5 步：撰写全稿与自检
按 `proposal_template.md` 补齐其余六要素（背景缺口、问题目标、风险、成果考核、引用映射）。风险章节的决策时点须与本版里程碑对齐。
```bash
python3 scripts/validate_proposal.py /app/work/proposal.md --profile roadmap --report /app/output/validation_report.json
python3 scripts/build_output.py --work /app/work --out /app/output --case /input/case.json
```
重点核对：时间轴表达完整；里程碑有验收标准；核算表三项（工时/经费/数据人员）有结论。

## 输出契约

可编辑稿件（含路线步骤表、资源核算表、里程碑表、甘特图章节）+ 真实渲染 PDF/PNG + `gantt.png` + `result.json` + `validation_report.json`。所有数字（工时、经费、缓冲）标注来源：材料给定 / 依据某文献[n] / 经验假设（待确认）。

## 异常处理

- **周期或经费在材料中缺失**：以“待导师/项目方确认”占位并给两套方案（保守/紧凑），status=partial。
- **核算不通过且无法并行/裁剪**：明确报告不可行，给出所需最小追加资源，不假装排得开。
- **工时无依据**：标注“经验估计（依据待补）”，写入 uncertainty。
- **里程碑被要求提前但关键路径不允许**：拒绝，说明关键路径依据。

## 资源文件

- `templates/route_steps.md`、`templates/resource_check.md`、`templates/milestones.md`、`templates/proposal_template.md`
- `checklists/quality_checklist.md`（C 组“排得开”为重点核查项）
- `scripts/validate_proposal.py --profile roadmap`、`scripts/build_output.py`（含甘特渲染）

## 最小调用示例（示意）

给定 T=24 个月、B=30 万、P=2 人。输出稿件含：步骤表 S1–S6（关键路径 S1→S3→S5）、核算表（Σ工时 40 人月 ≤ 2×24×0.8=38.4 不通过 → 并行 S2/S4 后 34 人月，通过）、里程碑 M1–M4、`gantt.png`、`result.json`。
