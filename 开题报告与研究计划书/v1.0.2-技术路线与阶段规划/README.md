# v1.0.2 技术路线与阶段规划 — 使用说明

## 这个 Skill 做什么
把技术路线拆成带输入/输出/依赖/工时的步骤，构造依赖图并标注关键路径，按给定周期、经费、人员做可行性核算（排不排得开是可计算的），再把可行后的步骤映射为带验收标准的里程碑并渲染甘特图。

## 调用方式
1. 准备 `/input/case.json`、`/input/task.md`（含周期 T、经费 B、人员 P 等约束）。
2. 按 `templates/route_steps.md` 拆步骤，`templates/resource_check.md` 做核算，`templates/milestones.md` 排里程碑；把里程碑同步写入 `/app/work/milestones.json`（`[{"id","label","start_month","end_month"}]`）以渲染甘特图。
3. 按 `templates/proposal_template.md` 撰写 `/app/work/proposal.md`，然后：
   ```bash
   python3 scripts/validate_proposal.py /app/work/proposal.md --profile roadmap --report /app/output/validation_report.json
   python3 scripts/build_output.py --work /app/work --out /app/output --case /input/case.json
   ```

## 关键方法
- 关键路径：总工时最长依赖链；可并行段单独标注。
- 核算表四项：工时、关键路径、经费、数据/人员，逐项给通过/不通过结论与来源。
- 不可行不硬写：先并行化→裁剪目标→降级指标→申请追加资源，调整全程留痕。

## 适用边界
无约束条件时索要约束或给保守/紧凑两套方案并标 partial。

## 失败处理与自查
见 `SKILL.md` 异常处理；自检重点：时间轴完整、里程碑有验收标准、核算结论明确。
