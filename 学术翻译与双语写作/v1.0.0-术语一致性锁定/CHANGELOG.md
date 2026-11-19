# CHANGELOG

## v1.0.0（2026-11-19）

- 首个提交版本。句段级翻译管线 + 术语三类候选机选 + Agent 审定锁定 + 逐句段术语核对闭环。
- 共享管线：init_result / inspect_case（翻译方向嗅探）/ parse_manuscript（md/tex/txt/docx/pdf，
  中英混排句切分带缩写与小数保护）/ segment_builder（句段分类+受保护片段）/
  assemble_translation（纯译文+双语对照+溯源+变更 diff）/ report_builder /
  assemble_result / validate_output / render_previews。
- 本地合成案例端到端实测：术语漂移、缩写首现违规均可检出；修订闭环复检清零；
  validate_output PASS。详见 evaluation/test_texts.md（合成）。
