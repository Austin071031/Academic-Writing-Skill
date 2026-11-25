# CHANGELOG

## v2.0.3（2026-11-25）

- 父辈：v1.0.3-创新点差异定位（grant-innovation-precision，attempt 90810，66.67/100，final）。
- 改了啥（唯一一件事：厚度信息密度，R4 路线卡）：
  - `scripts/elements_check.py` 升级（命令行接口与 element_map.json 原有键兼容，仅新增字段）：
    ① 厚度阈值上提——立项依据≥600 字、技术路线≥450 字、研究基础与可行性≥400 字、
    其余≥250 字（inspection 覆盖只能上调）；② 新增证据密度检查——事实类要素
    （立项依据/研究内容/技术路线/研究基础与可行性）引用不同 FID 数 ≥3 为达标，
    否则 element_map 中该要素 density_status="low"（新增键）；③ 对 thin 或
    density=low 要素在 element_findings.json 的 suggestion 字段写入可执行扩展指令——
    该要素尚未引用但相关的 FID 候选（按要素规则匹配台账，≤8 条，格式
    "可考虑补入：F0012 number 26.1%（F1-P003）；…"）+ 缺失子点提示（立项依据查
    现状/瓶颈/我们三环）；④ element_mapping.md 表格新增"证据密度"列。
  - `SKILL.md`：frontmatter description 换一句点明本版（name 不变）；第 7 步厚度/
    密度写作要求更新；第 12 步新增"厚度/密度强制扩展环"——存在 thin/low 要素必须
    按 suggestion 扩展 sections 并重跑 draft_builder→elements_check，直至全 ok 或
    预算兜底（模型请求 >40 → 交付 partial 并在 uncertainty 如实标注未达标要素）。
- 没动啥：其余 12 个脚本（含 innovation_engine.py）与父辈 md5 一致、逻辑零改动；
  三条红线、证据标记语法〔F〕〔拟〕〔确认〕、输出契约（result.json 键、产物清单）不变。
- 文档精简形：删除 docs/、evaluation/、SUBMISSION.md；references 三篇合并为
  method_rules.md（机检规则+创新点方法+失败模式）与 worked_example.md；
  保留 SKILL.md/README.md/GITHUB_URL.txt/examples/minimal_example.md。
- 提分依据：完整性 5 分（"七个要素是否齐全、厚度是否与任务要求匹配"由机检阈值
  上提+强制扩展环直接保证）+ 正确性 15 分（事实密度 ≥3 FID 机检保证章节稿有
  台账事实支撑而非提纲式空话）。
- 回归证据：见 `regression_report.json`（合成案例端到端真跑：12/13 脚本 md5 与
  父辈一致、引擎未改、element_map.json 原有键保留实测、result.json 键相同、
  validate ALL PASS、single_change 声明确认）。

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
