# CHANGELOG

## v1.0.2（2026-11-19）

- 主攻方向切换为"论证链与论据对应"（argument-chain-audit），六维普查兜底不变。
- 新增主攻引擎 `scripts/chain_audit.py`：
  - 论断抽取与四型分类（比较/因果/概括/绝对）；
  - 论据锚点三级窗口（句/段/相邻段：引用、图表与交叉引用、带单位数字）；
  - 论断—论据映射三档裁决 strong/weak/none（chain_audit.json 全程可复核）；
  - 深度检查：逻辑跳跃（前 3 段新词比例≥0.6）、疑似循环论证（3-gram Jaccard≥0.7 且双无锚点，confidence≤0.6 需人工确认）、论据强度不足（因果/绝对论断 vs 相关性/单点数据）、比较无对象；
  - findings ≤15 条，dimension=argument_chain。
- 管线：init_result / inspect_case / parse_manuscript / six_scan / chain_audit / report_builder / assemble_result / validate_output（纯标准库，共享核心未改动）。
- 交付：diagnosis_report.md / edit_plan.json / findings.json / chain_audit.json / result.json（契约字段回填）。
- 自测：evaluation/test_texts.md 合成稿（埋入 6 类问题）+ /tmp 外部样例，8 步管线均 validate PASS；命中明细见 test_texts.md。
- 异常路径：无稿件、PDF 降级、平铺文本、多稿件、截断、无文献/图表（锚点类型受限标注）、脚本异常，共 7 类。

维护：共享阈值集中于 scripts/scanutil.py THRESH；本引擎阈值在 scripts/chain_audit.py TH；新增误报模式请登记 references/failure_modes.md。
