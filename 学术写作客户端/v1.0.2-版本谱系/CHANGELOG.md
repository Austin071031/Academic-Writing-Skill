# CHANGELOG

## v1.0.2（2026-11-19）

- 初始版本：版本管理方向。
- sha256 内容寻址不可变快照 + lineage.json 谱系 manifest（parent 链/来源/摘要）
  + 段落级版本 diff + restore/verify 可校验回退；从机制上消除无法对应来源的副本。
- 全部脚本纯 Python 标准库实现；快照/diff/回退/完整性校验自测通过。
- 玻尔产品周赛第四期 学术写作客户端 参赛版（attempt 89298）。
