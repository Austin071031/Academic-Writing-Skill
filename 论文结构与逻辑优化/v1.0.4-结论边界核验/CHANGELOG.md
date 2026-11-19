# CHANGELOG

## v1.0.4（2026-11-19）

- 首次发布：主攻"结论边界与表述尺度"，六维普查兜底。
- 管线：init_result / inspect_case / parse_manuscript / six_scan / boundary_audit / report_builder / assemble_result / validate_output（纯标准库，共享核心复用 v1.0.0 同源脚本）。
- 主攻引擎 boundary_audit.py：
  - 数字溯源三层匹配（逐字 / 等值换算 / 舍入容差 5% + 舍入一致性约束），年份与图表编号剔除；
  - 摘要-结论同语境数字一致性（Jaccard≥0.4 句对）；
  - 因果表述三档（supported / overreach / unverifiable）；
  - 绝对化与推广超界（范围词 × 方法实验章条件枚举）；
  - 限制说明四态审计（missing / misplaced / insufficient / adequate）。
- 交付：diagnosis_report.md / edit_plan.json / findings.json / boundary_audit.json / result.json（契约字段回填）。
- 异常路径：无稿件、PDF 降级、平铺文本、多稿件、截断、无方法/实验章、脚本异常，共 7 类。
- 已知共享脚本问题（仅记录，未改动）：six_scan.py D6 无源数字检查仅逐字匹配，对舍入数字（65% vs 65.2%）误报，第 7 步以 boundary_audit.json verdict 为准删除（见 references/failure_modes.md）。

维护：阈值集中于 scripts/boundary_audit.py 顶部常量（APPROX_TOL / ECHO_JACCARD / SCOPE_CUES / ENTITY_RE）；新增误报模式请登记 references/failure_modes.md。
