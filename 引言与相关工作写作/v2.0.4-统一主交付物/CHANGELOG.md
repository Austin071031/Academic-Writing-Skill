# CHANGELOG

## v2.0.4（2026-11-25，父版本 v1.0.0，attempt 89635 得分 62.67）

- **单点改动（统一主交付物）**：assemble_result.py 增出 paper_sections.md——将引言、相关工作、
  参考文献、证据映射附录（附录A）与机读核验摘要（附录B）合并为一份自包含成稿，
  便于评审一次读取"可直接进入论文"的完整产物。
- 目标评分项：任务完成度 15（可直接进入论文）+ 完整性 5。
- 其余管线与 v1.0.0 完全一致。

## v1.0.0（2026-11-19）

- 首个参赛版本：研究背景方向。
- 共享管线：inspect → parse_manuscript/parse_library/parse_notes → extract_facts →
  anti_fluff → build_deliverables（锚点核验/论断-引用绑定/GB-T 7714 渲染）→
  assemble_result → validate_output → render_previews。
- 创新点：背景句级证据锚定 + 空转铺垫确定性审计（内置 8 类句式 + 可扩展词表文件），
  与 evidence_map 双向回溯。
