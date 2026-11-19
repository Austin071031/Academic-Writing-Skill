# v1.0.1 问题定义与目标对齐 — 使用说明

## 这个 Skill 做什么
把宽泛研究方向收敛为 1—3 个可证伪研究问题，为每个问题生成可考核目标（指标、阈值及依据、样本、对照、时间点），并用对齐追踪矩阵强制“问题—目标—路线—里程碑—成果”逐行对应，杜绝各章节各写各的。

## 调用方式
1. 准备 `/input/case.json`、`/input/task.md`。
2. 按 `templates/question_objective_matrix.md` 定问题与目标，按 `templates/traceability_matrix.md` 建对齐矩阵，按 `templates/proposal_template.md` 撰写 `/app/work/proposal.md`。
3. 校验与构建：
   ```bash
   python3 scripts/validate_proposal.py /app/work/proposal.md --profile objective --report /app/output/validation_report.json
   python3 scripts/build_output.py --work /app/work --out /app/output --case /input/case.json
   ```

## 关键方法
- 三问过滤收敛：可回答、可证伪（写否定判据）、值得做。
- 阈值必须有依据：材料/文献，否则标“假设值，待导师确认”。
- 漂移检测：任何章节内容挂不上对齐矩阵即删除或改写。

## 适用边界
须有输入材料与基本约束（周期/经费/数据）；约束缺失时标 partial 并给候选方案。

## 失败处理与自查
见 `SKILL.md` 异常处理；自检重点：问题数=目标数、每目标四要素齐全、矩阵每行闭合。
