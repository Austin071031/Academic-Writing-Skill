# CHANGELOG

## v1.1.0（2026-11-24，父版本 v1.0.0，attempt 89635 得分 62.67）

- **最小单点改动：论断-引用绑定由 Agent 逐字登记（claim_bindings.jsonl）改为引擎自动派生**
  ——evidence_map 增加 cite 字段；草稿中的 〔E#〕 锚点即绑定，引擎按锚点所在句自动注入 [n]。
  消除"绑定句非逐字→绑定 missed"这一最脆弱环节（v1.0.0 实测最大漏配来源），
  并将 Agent 登记文件从 5 个减至 4 个，降低执行预算压力。
- 兼容性：claim_bindings.jsonl 若存在仍被读取合并（建议不再写）。
- build_report.json 增加 bindings.auto_derived 计数。
- 本地合成案例实测：零 bindings 文件下锚点 22/22、自动绑定 18/18、文献 7 条、
  四要素全 true、validate PASS，成稿与 v1.0.0 等价。

## v1.0.0（2026-11-19）

- 首个参赛版本：研究背景方向。
- 共享管线：inspect → parse_manuscript/parse_library/parse_notes → extract_facts →
  anti_fluff → build_deliverables（锚点核验/论断-引用绑定/GB-T 7714 渲染）→
  assemble_result → validate_output → render_previews。
- 创新点：背景句级证据锚定 + 空转铺垫确定性审计（内置 8 类句式 + 可扩展词表文件），
  与 evidence_map 双向回溯。
