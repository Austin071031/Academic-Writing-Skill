# CHANGELOG

## v1.0.1（2026-11-19）

- 参赛版本（玻尔产品周赛 写作14｜基金申请书写作，challenge-d403dce6），方向：科学问题收敛。
- 共享核心管线 12 脚本：init_result / inspect_case / parse_materials / fact_ledger /
  draft_builder / source_audit / elements_check / report_builder / assemble_result /
  validate_output / render_previews / grant_utils。
- 专属引擎 question_engine.py：seed（gap/未知信号词问题候选机选 + 材料/task.md 宽泛表述警示）
  + audit（missing_section / question_count / no_decomposition / no_boundary /
  scope_too_broad / method_misaligned 六规则）。
- 科学问题收敛判据首次落地：可回答（1-3 个问句式核心问题）、可分解（问题树标记）、
  有边界（边界声明词）、不过大（宽泛表述黑名单）、问题—目标—路线对齐（trigram 相似度阈值 0.05）。
- 证据标记语法〔F〕〔拟〕〔确认〕与三级对应（段落→要素→证据）沿用共享核心。
