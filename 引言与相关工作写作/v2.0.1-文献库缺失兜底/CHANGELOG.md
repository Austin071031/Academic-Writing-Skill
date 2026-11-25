# CHANGELOG

## v2.0.1（2026-11-25，父版本 v1.0.0，attempt 89635 得分 62.67）

- **单点改动（文献库缺失兜底）**：新增 scripts/salvage_library.py——library.json 为空时从稿件
  参考文献段与笔记编号条目抢救文献记录（GB/T 7714/编号英文/APA 形态），逐条标注
  salvage_confidence；已有文献库时 no-op。SKILL.md Phase 1 增加一条幂等命令与低置信登记要求。
- 目标评分项：运行稳定性 4 + 异常处理 3（真实案例材料形态未知，bib 缺失不再致命）。
- 其余管线与 v1.0.0 完全一致。

## v1.0.0（2026-11-19）

- 首个参赛版本：研究背景方向。
- 共享管线：inspect → parse_manuscript/parse_library/parse_notes → extract_facts →
  anti_fluff → build_deliverables（锚点核验/论断-引用绑定/GB-T 7714 渲染）→
  assemble_result → validate_output → render_previews。
- 创新点：背景句级证据锚定 + 空转铺垫确定性审计（内置 8 类句式 + 可扩展词表文件），
  与 evidence_map 双向回溯。
