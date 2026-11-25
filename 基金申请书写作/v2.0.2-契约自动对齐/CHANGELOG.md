# CHANGELOG

## v2.0.2（2026-11-25）— 契约自动对齐（R3 单点迭代）

- 父辈：v1.0.3-创新点差异定位（grant-innovation-precision，attempt 90810，66.67/100）。
- **改了啥（唯一一件事）**：output_contract 契约自动对齐——
  - 新增 `scripts/contract_check.py`（stdlib only、幂等、`--work`/`--out` 必填）：
    从 work/inspection.json 取 output_contract_fields，逐字段语义映射到实际产物
    （稿/draft/章节→proposal_draft.md；对照/映射/map/要素→element_mapping.md；
    报告/report→report.md；溯源/证据/evidence/来源→result.json#evidence_map；
    预览/preview→preview.html；留痕/标注→proposal_annotated.md；无法映射→null+原因），
    机检产物存在且非空，写 work/contract_map.json（{field:{artifact,note,status}}），
    任一 missing 打印 FAIL 清单但 exit 0（如实记录，不阻断）；无契约字段时优雅跳过。
  - `scripts/assemble_result.py` 最小补丁：回填 output_contract 时优先读
    work/contract_map.json（缺失则走原关键词映射逻辑），每字段填
    {"artifact": 相对路径或 null, "note": 一句中文内容说明}；函数签名与默认行为兼容。
  - `SKILL.md`：validate 前加 contract_check 一步（首跑生成 contract_map.json，
    assemble 后幂等复跑确认）；输出物清单表加"契约字段→产物映射（contract_map.json）"行；
    frontmatter name 保持 grant-innovation-precision，description 换一句点明本版。
  - 文档精简形（对齐 v2/v3 打包修复）：删 docs/、evaluation/、SUBMISSION.md；
    references 3 合并为 method_rules.md + worked_example.md；README/GITHUB_URL 指向本版。
- **没动啥**：其余 12 个脚本与父辈 md5 逐字节一致（含 innovation_engine.py 引擎零改动）；
  三条红线、证据标记语法〔F〕〔拟〕〔确认〕、result.json 顶层键与产物清单不变。
- **提分依据**：契约逐字段语义化兑现 + 机检存在性，直接对应评分维度
  "实际效果-任务完成度 15 分"与"可核验性"；缺失字段如实 FAIL 记录而非静默跳过。
- **回归证据**：见版本根目录 `regression_report.json`（合成案例端到端真跑：
  12 脚本 md5 一致、引擎未改、assemble_result 补丁默认行为与父辈输出一致、
  result.json 顶层键相同、validate ALL PASS）。

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
