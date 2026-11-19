# CHANGELOG

## v5.0.0（2026-11-19）

- 首个版本：两层核验（条目级真实性体检 + 论断级引用匹配裁决）。
- verify_engine.py：doi_syntax / year_plausibility / field_conflict / duplicate_title_in_library /
  title_ends_with_period 五项本地确定性体检；--online 模式逐条 DOI 核验 Crossref（5s 超时，
  verified_online / metadata_mismatch / unverified_offline 三态如实记录）。
- match_verdicts.jsonl 覆盖率审计：缺漏段落列出并在 annotated_manuscript.md 标注 ⚠ 缺裁决。
- 联动 cite_engine audit：编号越界/缺口/样式混杂结论并入 verification_report。
- 产物：verification_report.json / verification_report.md / annotated_manuscript.md / evidence_map.json。
