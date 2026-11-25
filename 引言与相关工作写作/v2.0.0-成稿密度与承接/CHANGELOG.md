# CHANGELOG

## v2.0.0（2026-11-25，父版本 v1.0.0，attempt 89635 得分 62.67）

- **单点改动（成稿密度与承接）**：引言/相关工作篇幅目标由 400–900/400–1000 字上调至
  800–1500 字；增加四部分显式承接要求（背景末句→空白首句→贡献首句的链条约束）与
  SKILL.md 内联正面样板；引擎长度告警阈值 250/350 → 600/600。
- 目标评分项：任务完成度 15（"四部分齐全且彼此承接、可直接进入论文"）+ 完整性 5。
- 其余管线与 v1.0.0 完全一致。

## v1.0.0（2026-11-19）

- 首个参赛版本：研究背景方向。
- 共享管线：inspect → parse_manuscript/parse_library/parse_notes → extract_facts →
  anti_fluff → build_deliverables（锚点核验/论断-引用绑定/GB-T 7714 渲染）→
  assemble_result → validate_output → render_previews。
- 创新点：背景句级证据锚定 + 空转铺垫确定性审计（内置 8 类句式 + 可扩展词表文件），
  与 evidence_map 双向回溯。
