# CHANGELOG

## v1.0.3（2026-11-19）

- 参赛版本（玻尔产品周赛 写作14｜基金申请书写作），方向：创新点差异定位与不可核验修饰清理。
- 共享核心管线 12 脚本原样复制（init_result / inspect_case / parse_materials / fact_ledger /
  draft_builder / source_audit / elements_check / report_builder / assemble_result /
  validate_output / render_previews / grant_utils），接口未改。
- 专属引擎 innovation_engine.py：
  - seed：从 fact_ledger 与 materials 机选代表性已有工作对比锚点（paper 角色材料的
    citation/pub_mention 类事实）+ gap 上下文 → work/innovation_seed.json；
  - audit：审计创新点节（兼容 特色与创新/创新与特色）五类规则——missing_section(high)、
    banned_modifier(high，10 词黑名单+替换指令)、no_baseline_anchor(medium)、
    no_difference_statement(medium)、three_dim_incomplete(medium，缺维写明)。
- 证据标记语法〔F〕〔拟〕〔确认〕与差异定位三段式（锚定已有工作→差异表述→凭什么成）落地；
  references/innovation_method.md 含 10 组空泛→可核验替换句式库与三维判据。
