# CHANGELOG

## v1.0.2（2026-11-19）

- 参赛版本（玻尔产品周赛 写作14｜基金申请书写作，challenge-14），方向：
  目标—内容—路线—指标逐条对应（slug: grant-alignment-matrix）。
- 共享核心管线 12 脚本：init_result / inspect_case / parse_materials / fact_ledger /
  draft_builder / source_audit / elements_check / report_builder / assemble_result /
  validate_output / render_previews / grant_utils（与 v1.0.0/v1.0.1 同版复制，接口未改）。
- 专属引擎 alignment_engine.py：
  - `seed`：解析 draft.json 四节编号条目（1./（1）/（一）/①/目标一/内容一/步骤一/指标一/
    第一条等行首体例；无编号按段落整体切条并记 note）→ work/alignment_seed.json，
    打印四节计数供写作前/落稿后自查条目数设计；
  - `audit`：跨节条目 trigram 相似度矩阵（阈值 0.12）+ 编号互引图谱 → 覆盖规则
    （每目标≥1 内容、每内容≥1 路线、每指标≥1 目标）、数量一致性（count_mismatch high，
    写明"目标 3 条、路线 2 条"式事实）、缺节（missing_section high）→
    work/alignment_matrix.json + work/findings.json + alignment_table.md（--out）。
- 考核指标节识别：element ∈ {考核指标, 预期成果} 全段落，或研究目标节内含
  指标/考核/预期 信号的段落。
