# CHANGELOG

## v1.0.0（2026-11-19）

- 初始版本：修订追踪方向。
- DOCX 原生修订（w:ins/w:del）落地 + changes.json 逐条台账（位置/原文/改后/依据/状态）
  + accepted/rejected 双变体 + audit_diff 保真核验 + render_preview 预览渲染
  + result_builder 契约化诚实 result.json。
- 全部脚本纯 Python 标准库实现；针对合成案例完成端到端自测。
- 玻尔产品周赛第四期 学术写作客户端 参赛版（attempt 89291）。
