# CHANGELOG

## v1.0.2（2026-11-19）
- 本方向首版（术语与引用、论断溯源）：
  - 新增 `trace_engine.py`：`bind`（四种引用样式 → 文献条目绑定，unbound=critical）、
    `verify`（引用存在性 / 数值 verbatim-derived-unverified / 语气升格与否定翻转载定候选 /
    漏引 top3 推荐）、`render_refs`（GB/T 7714-2015 顺序编码渲染 + 编号双向一致交叉核对）、
    `annotate`（不改正文的 ⚠ 批注稿）。
  - 数值遮蔽：图表号/章节号/年份/引用标记/化学式内嵌数字；derived 含百分比换算与两值四则（±1%）。
  - 语气阶梯 L1-L4，升格判定要求 claim≥L4 防误报；漏引豁免"数值全部可溯源"的自有数据段。
- 测试：合成案例端到端 validate_output PASS；负例（[5] 越界、"完全解决"升格、9.9 臆造数值）
  三类缺陷全部检出；正例（[1][2]+材料数值）零误报；author_year「Zhang 等, 2023」绑定回归通过。
- 修复：norm_surname 对"Zhang 等"因含 CJK 字符误入中文分支导致绑定失败的问题；
  annotate 批注定位由 list.index 改为原始行号聚合，避免重复行错位。
