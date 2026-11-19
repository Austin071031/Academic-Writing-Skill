# CHANGELOG

## v1.0.0（2026-11-19）

首个提交版本（attempt 89023）。

- 九阶段流水线：案例解析 → 模板实测 → 规格合并 → 源稿转换 → 结构化套用 → 保真核验 → 合规核验 → 渲染导出（目录两遍回填页码）→ 结果组装。
- 纯标准库 OOXML 引擎：schema 顺序插入、OPC 关系/内容类型自动注册、默认命名空间序列化、写穿缓存。
- 合成夹具全流程验证：9 阶段全部 success、fidelity PASS、compliance 21 PASS / 0 FAIL；边界回归（PDF 源稿有损重建标 partial、case.json 缺失合成、模板扫描兜底）通过。
- 文档：SKILL.md、usage.md、spec_schema.md、troubleshooting.md、example.md。
