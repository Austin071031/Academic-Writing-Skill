# CHANGELOG

## v1.0.3（2026-11-19）

- 初始版本：文档导出方向。
- 导出管线四步：font-check 字体度量兼容检查 → 真实渲染（soffice→PDF→PNG）
  → toc-refresh 两遍渲染实测页码回填（保留域结构）→ fidelity 内容单元级
  before/after 差分；全程可降级且留痕，不伪造预览。
- 全部脚本纯 Python 标准库实现；渲染与差分自测通过。
- 玻尔产品周赛第四期 学术写作客户端 参赛版（attempt 89299）。
