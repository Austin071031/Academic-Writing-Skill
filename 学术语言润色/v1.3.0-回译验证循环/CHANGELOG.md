# CHANGELOG

## v1.3.0（2026-11-23）— 回译验证循环（首版）

- 核心机制：关键句（数值/引用/限定词/否定/因果）modify 后强制回译，主张矩阵
  （hedging/numbers/units/citations/pointers/causality/negation 七格）逐格比对，
  不一致修复、两轮仍漂移则回退 keep 并列人工确认。
- segment_util.py：一站式预检，自动标注【K】关键句；claims_check.py：机读复核
  回译留痕与 claims 逐格一致性；assemble.py 产出 drift_report.md 漂移报告。
- 与 v1.1.0 的 guard_check 差异：guard 看"原文 vs 改文"的表面特征，回译循环看
  "原文 vs 回译文"的语义等价，能抓住同义改写掩盖下的命题漂移。

- 提交：playground attempt 99594（product-arena-02-7051d92d，写作02｜学术语言润色）
