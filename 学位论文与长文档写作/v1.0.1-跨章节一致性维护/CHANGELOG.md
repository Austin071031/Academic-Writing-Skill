# CHANGELOG

## v1.0.1（2026-11-19）
- 新增 `consistency_engine.py`（纯标准库，三个子命令）：
  - `scan`：术语候选三类（缩写定义型/引号书名号型/高频复合词）、交叉引用审计
    （dangling=critical 供 validate_output 消费、unreferenced=warn、同章编号连续性）、
    跨章结论句矛盾候选（主语 n-gram 重叠≥0.3 且极性相反）。
  - `glossary`：按 Agent 审定的 glossary_review.json 生成术语表与同概念异写报告
    （规范化：小写/连字符/全半角/单复数；定义处豁免；重叠命中只计最长写法；
    double_definition 与 symbol_clash 冲突检测）。
  - `impact`：--changed-term / --changed-sid 单点改动影响面（术语命中 + xref 指向 +
    结论句重叠传播）。
- 中文术语左侧虚词剥离（"是全固态电池"→"全固态电池"）；"中文（EIS）"型纯缩写定义识别。
- SKILL.md：Phase 0-5 流程、三条红线（不臆造术语定义/不臆造核验结果/术语统一必须
  走引擎复核）、11 类异常处置表、40 次请求预算兜底。
- 端到端验证：主合成案例全流程 validate_output PASS；负例（三写法混用+悬空图3-1）
  检出异写 3 处与 dangling 1 处；反例（写法统一+引用有定义）零误报。
  见 evaluation/test_texts.md 与 examples/minimal_example.md。
