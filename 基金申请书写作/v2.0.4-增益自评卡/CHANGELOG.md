# CHANGELOG

## v2.0.4（2026-11-25）增益自评卡（R5 单点迭代）

- 父辈：v1.0.3-创新点差异定位（grant-innovation-precision，attempt 90810，66.67/100，final）。
- 改了啥（唯一一件事：使用增益可验证性单点迭代）：
  - 新增 `scripts/gain_card.py`（stdlib only、幂等、--work/--out 必填）：汇总各 findings
    文件与 change_log.json、stats.json → out/gain_card.md 三节——①反事实缺陷表
    （按 kind 聚合计数+真实定位示例，0 处类别如实标注不编造）②修订闭环表（change_log 按 op
    聚合+各 findings 当前 high/medium/low 统计+历史快照如实说明）③机械劳动清单
    （脚本+替代的人工核对项，数字实读 stats.json/各 json）。
  - `scripts/report_builder.py` 最小补丁：若 out/gain_card.md 存在，在 report.md 末尾追加
    "## 增益自评卡"节并嵌入全文；不存在则行为与父辈完全一致（实测字节级一致）。
  - `SKILL.md`：第 13 步 report_builder 前加 gain_card 命令；输出物清单表加 gain_card.md 行；
    frontmatter name 保持 grant-innovation-precision，description 换一句点明本版。
  - 打包精简形：删 docs/、evaluation/；references 3 个合并为 method_rules.md +
    worked_example.md；README/GITHUB_URL 同步指向本版。
  - 改动文件：scripts/gain_card.py（新增）、scripts/report_builder.py（补丁）、SKILL.md、
    README.md、GITHUB_URL.txt、CHANGELOG.md、references/method_rules.md（合并）。
- 没动啥：其余 12 个脚本（11 共享核心 + innovation_engine.py）与父辈 md5 一致、逻辑零改动；
  三条红线、证据标记语法〔F〕〔拟〕〔确认〕、输出契约（result.json 键、产物清单）不变。
- 提分依据：使用增益 25 中"增益可验证性 5 分"与创新增益"证据 5 分"需要显式对照证据；
  父辈只有分散的 findings，没有聚合的反事实对照（"基础 Agent 会错什么 vs 本交付"）。
- 回归证据：见本目录 regression_report.json（合成案例真跑：scripts_same/engine_same/
  pipeline_exit0/validate PASS/result.json 键相同/report_builder 无 gain_card 时与父辈一致）。

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
