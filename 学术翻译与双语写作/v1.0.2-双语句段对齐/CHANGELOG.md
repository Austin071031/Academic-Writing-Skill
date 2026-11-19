# CHANGELOG

## v1.0.2（2026-11-19）

- 首个提交版本。对齐计划 + 结构不变量 + 逐句段状态核对 + 段首 PID 双语对照稿。
- 句段六分类（heading/body/caption/footnote/formula/reference）；参考文献按 [n] 逐条拆分。
- 本地合成案例端到端实测：缺译、错号、漏译从句、未知 ID 均可检出；
  validate_output PASS。详见 evaluation/test_texts.md（合成）。
