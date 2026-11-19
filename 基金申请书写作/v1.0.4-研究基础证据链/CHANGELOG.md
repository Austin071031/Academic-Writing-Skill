# CHANGELOG

## v1.0.4（2026-11-19）

- 参赛版本（玻尔产品周赛 写作14｜基金申请书写作，challenge-d403dce6），方向：研究基础与可行性证据链、已完成/拟开展区分。
- 共享核心管线 12 脚本（与 v1.0.0 同源原样复制）：init_result / inspect_case / parse_materials /
  fact_ledger / draft_builder / source_audit / elements_check / report_builder / assemble_result /
  validate_output / render_previews / grant_utils。
- 专属引擎 feasibility_engine.py：
  - seed：prior_work 角色文件段落（及含 申请人/本团队/平台/实验室 信号的其他文件段落）机选证据链行
    → work/evidence_chain_seed.json（能力短语=段落前 30 字，证据 FID 自动关联，relation_to_project 留空）。
  - audit：研究基础节六条规则——missing_section(high) / aspect_violation_planned_as_done(high) /
    aspect_violation_done_as_planned(medium) / unsourced_achievement(high) /
    chain_incomplete(medium；未生成审定版则 low) / feasibility_missing(low)。
- 文档体系：SKILL.md（13 步工作流，第 6 步审定证据链另存 evidence_chain.json）、
  references/{feasibility_method,failure_modes,worked_example}.md、evaluation/ 合成测试文本。
