# v1.0.0 研究缺口与证据提炼 — 使用说明

## 这个 Skill 做什么
把输入材料拆成编号证据（E1…En），用“已知—未知—待验证”矩阵推导研究缺口，再收敛出 1—3 个可证伪的研究问题，最后补齐七要素开题报告并交付可编辑文件与结构化 result.json。它保证背景章节每句论断可回溯、缺口由证据推导而非文献罗列。

## 调用方式
评测平台将本目录安装为 Skill 后，Agent 在案例中按 `SKILL.md` 工作流程执行；本地或人工调用步骤：

1. 准备 `/input/case.json`、`/input/task.md`。
2. 按 `templates/evidence_register.md` → `gap_matrix.md` → `proposal_template.md` 撰写 `/app/work/proposal.md`。
3. 校验与构建：
   ```bash
   python3 scripts/validate_proposal.py /app/work/proposal.md --profile gap --report /app/output/validation_report.json
   python3 scripts/build_output.py --work /app/work --out /app/output --case /input/case.json
   ```

## 关键方法
- 证据清单先行：先登记后写作，写作中只允许使用已登记证据。
- 缺口推导链：每条缺口标注由哪些已知（≥2 条）推出；证据不足的缺口显式标为假设。
- 反综述自检：逐句删除与缺口无指向关系的背景句。

## 适用边界
必须有输入科研材料；无材料时输出“待确认”框架并标 partial，不编造背景。

## 失败处理与自查
见 `SKILL.md` 异常处理；`validation_report.json` 的 `hard_failures` 必须为空方可提交。
