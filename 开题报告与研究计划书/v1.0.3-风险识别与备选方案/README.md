# v1.0.3 风险识别与备选方案 — 使用说明

## 这个 Skill 做什么
用预尸检（pre-mortem）从数据获取、方法可行性、进度、伦理与合规、经费五类生成风险，为每条风险补齐可观察触发信号、影响范围、具体备选方案与决策时点，并把备选方案回写到阶段计划与经费科目，做到风险与计划联动。

## 调用方式
1. 准备 `/input/case.json`、`/input/task.md`。
2. 按 `templates/risk_register.md` 建风险登记册，决策时点与里程碑对齐；把备选方案落点写入计划章节。
3. 按 `templates/proposal_template.md` 撰写 `/app/work/proposal.md`（风险登记册作为一章），然后：
   ```bash
   python3 scripts/validate_proposal.py /app/work/proposal.md --profile risk --report /app/output/validation_report.json
   python3 scripts/build_output.py --work /app/work --out /app/output --case /input/case.json
   ```

## 关键方法
- 触发信号量化优先（如“第 6 月末样本 < 计划 60%”），无法量化则写明定性监测责任人与检查里程碑。
- 备选方案必须具体到动作，禁用“加强管理”类空话。
- 每条备选在登记册“落点”列注明计划/经费/里程碑位置。

## 适用边界
材料未涉及的类别仍列出并标注“材料未涉及，按规范补列”，触发与处置标“待确认”。

## 失败处理与自查
见 `SKILL.md` 异常处理；自检重点：五类覆盖、四要素齐全、备选有落点。
