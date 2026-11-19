# CHANGELOG

## v1.0.0（2026-11-19）

- 首个发布：主攻"研究问题与贡献主张对齐"，六维普查兜底。
- 管线：init_result / inspect_case / parse_manuscript / six_scan / rq_engine / report_builder / assemble_result / validate_output（纯标准库）。
- 主攻引擎：RQ×章节覆盖矩阵、贡献×证据三档裁决、首尾呼应矩阵（rq_map.json）。
- 交付：diagnosis_report.md / edit_plan.json / findings.json / rq_map.json / result.json（契约字段回填）。
- 异常路径：无稿件、PDF 降级、平铺文本、多稿件、截断、无文献/图表、脚本异常，共 7 类。

维护：阈值集中于 scripts/scanutil.py THRESH；新增误报模式请登记 references/failure_modes.md。
