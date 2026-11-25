# CHANGELOG

## v2.0.0（2026-11-25）— 快速主通道（管线减负单点迭代，R1）

- 父辈：v1.0.3-创新点差异定位（grant-innovation-precision，attempt 90810，66.67/100）。
- 改了啥（唯一一件事：管线减负——骨架预生成 + 预算表）：
  - 新增 `scripts/sections_scaffold.py`（stdlib only、幂等、--work 必填）：读
    fact_ledger.json + inspection.json，生成 work/sections/01..07 七个骨架
    （`# 要素名` + 字数目标注释 600/450/400/250 + 按要素关键词与 role_guess
    匹配的 FID 候选清单（HTML 注释，≤12 条，列 fid/type/value/unit/来源 pid）
    + 待填槽位【在此撰写：…】；含〔F〕标记的文件不覆盖）。
  - `SKILL.md`：工作流从 13 步压缩为 8 步主通道（init→inspect→parse→ledger→
    scaffold+seed→Agent 一轮写完七节→builder+三审计+innovation audit 一轮→
    report+assemble+validate+render）；顶部新增分阶段请求预算表（总预算≤40 请求）；
    复核修订环降级为"第二轮可选（剩余预算>15 才做）"；frontmatter description
    换入本版单点改动说明，name 保持 grant-innovation-precision。
  - 文档精简形：删 `docs/`、`evaluation/`、`SUBMISSION.md`；references 3 文件
    合并为 `references/method_rules.md` + `references/worked_example.md`；
    `README.md` 合并原 docs/USAGE.md；`examples/minimal_example.md` 同步 8 步流程；
    `GITHUB_URL.txt` 指向本版本目录。
- 没动啥：13 个既有脚本（12 共享核心 + innovation_engine.py）逻辑零改动
  （md5 与父辈一致）；三条红线、证据标记语法〔F〕〔拟〕〔确认〕、输出契约
  （result.json 键、产物清单）、七要素与厚度机检阈值均不变。
- 提分依据：评分摘要一致为 "Partial credit"，预算内截断（13 步 ~15 条命令 +
  读 6 个中间 JSON + 写 7 节，900 秒内易跳过修订环或压缩章节厚度）是最大失分
  嫌疑；骨架预生成 + FID 候选清单使 Agent 不必读 5 个中间 JSON 即可落笔，
  主通道压到 ≤40 请求，余量全部让给写作厚度，保证 900 秒内完整七节成稿。
- 回归证据：`regression_report.json`（机器真跑：13 脚本 md5 与父辈一致、
  端到端 pipeline exit 0、validate ALL PASS、scaffold 幂等实测、result.json
  键与父辈相同）。

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
