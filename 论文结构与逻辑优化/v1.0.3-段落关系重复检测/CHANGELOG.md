# CHANGELOG

## v1.0.3（2026-11-19）

- 首个发布（V4）：主攻"段落关系与重复内容"，六维普查兜底。
- 管线：init_result / inspect_case / parse_manuscript / six_scan / redundancy / report_builder / assemble_result / validate_output（纯标准库）。
- 主攻引擎（scripts/redundancy.py）：
  - 段落两两字符 3-gram Jaccard（n_char≥40）：≥0.55 重复（同章相邻→merge；跨章→删冗余侧+交叉引用，保留启发式：角色核心度优先、平级取先出现者）；0.30–0.55 近似重复（narrow）；摘要↔引言/结论高重叠单独标注"结构性呼应 vs 冗余"（confidence≤0.6 人工裁决）；
  - 句子级跨章近重复（3-gram ≥0.80）；
  - 衔接缺失（同章相邻段 lex<0.05 且无衔接词）+ 回指悬空（如前所述/this shows…但前 3 段无内容词重叠）；
  - 该拆分未拆分（≥400 字符且内部句均相似度<0.03，给出建议拆分句界）；
  - 统计：重复对数、涉及段落数、冗余字符估算；findings 上限 15；两两比较防爆上限 1000 段。
- 交付：diagnosis_report.md / edit_plan.json / findings.json / redundancy_report.json / result.json（契约字段回填）。
- 异常路径：无稿件、PDF 降级、平铺文本、多稿件、截断、无文献/图表、超量段落、脚本异常，共 8 类。

维护：阈值集中于 scripts/scanutil.py THRESH（引擎私有阈值在 redundancy.py 顶部常量）；新增误报模式请登记 references/failure_modes.md。
