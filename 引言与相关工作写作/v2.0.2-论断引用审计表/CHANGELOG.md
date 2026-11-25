# CHANGELOG

## v2.0.2（2026-11-25，父版本 v1.0.0，attempt 89635 得分 62.67）

- **单点改动（论断-引用审计表）**：build_deliverables.py 零 Agent 成本增出
  output/citation_audit_table.md——逐条列出 论断句→引用编号→文献题名/来源/年份→证据锚点/摘录，
  供评审逐条复核"引用落在具体论断上、元数据真实"。
- 目标评分项：可核验性 5（每条引用能否回到来源）+ 正确性 15 的复核便利。
- 其余管线与 v1.0.0 完全一致。

## v1.0.0（2026-11-19）

- 首个参赛版本：研究背景方向。
- 共享管线：inspect → parse_manuscript/parse_library/parse_notes → extract_facts →
  anti_fluff → build_deliverables（锚点核验/论断-引用绑定/GB-T 7714 渲染）→
  assemble_result → validate_output → render_previews。
- 创新点：背景句级证据锚定 + 空转铺垫确定性审计（内置 8 类句式 + 可扩展词表文件），
  与 evidence_map 双向回溯。
