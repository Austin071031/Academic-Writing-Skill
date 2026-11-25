# CHANGELOG

## v2.0.3（2026-11-25，父版本 v1.0.0，attempt 89635 得分 62.67）

- **单点改动（基线对照自证）**：新增 scripts/self_compare.py——Agent 补写一段"无 Skill 风格"
  基线段（work/baseline_intro.md），引擎用同一套确定性规则（空转铺垫命中、证据锚定比例、
  问题信号、绑定数、篇幅）在基线与成稿两侧各算一遍，输出 comparison_report.md 量化对照。
- 目标评分项：使用增益-可验证性 5（公平对照证明改善）+ 创新增益-创新证据 5。
- 其余管线与 v1.0.0 完全一致。

## v1.0.0（2026-11-19）

- 首个参赛版本：研究背景方向。
- 共享管线：inspect → parse_manuscript/parse_library/parse_notes → extract_facts →
  anti_fluff → build_deliverables（锚点核验/论断-引用绑定/GB-T 7714 渲染）→
  assemble_result → validate_output → render_previews。
- 创新点：背景句级证据锚定 + 空转铺垫确定性审计（内置 8 类句式 + 可扩展词表文件），
  与 evidence_map 双向回溯。
