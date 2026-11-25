# CHANGELOG

## v2.0.1（2026-11-25）示例成稿锚定（体裁厚度单点迭代）

- 父辈：v1.0.3-创新点差异定位（grant-innovation-precision，attempt 90810，66.67/100，final）。
- 改了啥（唯一一件事 + 文档精简形）：
  1. **新增 `examples/full_draft_example.md`**：完整合成七要素成稿示例（固态锂电池界面
     题材，与测试床钙钛矿不同，避免被当预制答案），顶部显著标注"合成示例，仅示范成稿
     形态与标记用法，非正式案例结果，禁止照抄内容"，并注明"示例 FID 对应示例台账，
     非本案例台账"。正文约 2983 字：立项依据现状—瓶颈—我们三段链（785 字，事实句
     逐句带〔F〕）、科学问题 1 核心 + 2 子问题 + 边界声明、研究目标 3 条、研究内容
     3 条、创新点 2 条（对比锚点 + 不同于/优于，无黑名单修饰词）、技术路线 3 步骤
     （含输入输出）、研究基础已完成带〔F〕/拟开展带〔拟〕体貌分清；目标-内容-路线
     编号互指可机检。
  2. **SKILL.md 第 7 步开头**改为："先通读 examples/full_draft_example.md 掌握成稿形态
     （厚度、标记密度、要素衔接），再按同样标准撰写本案例章节稿；示例内容禁止照抄。"
     frontmatter description 换入本版说明一句；name 保持 grant-innovation-precision。
  3. 文档精简形（铁律要求）：删 docs/、evaluation/；references 3 个合并为
     method_rules.md（innovation_method + failure_modes）+ worked_example.md；
     SKILL.md/README.md 中相应引用同步更新；唯一文件 21 个（≤22）。
- 没动啥：13 个脚本（12 共享核心 + innovation_engine.py）与父辈逐字节一致（md5 核验）；
  13 步工作流其余步骤、三条红线、证据标记语法〔F〕〔拟〕〔确认〕、输出契约
  （result.json 键、产物清单）均未改动。
- 提分依据：v1.0.3 评分摘要 "Partial credit — push for a more complete, genuinely-derived
  solution"，厚度/体裁不达标是主要丢分嫌疑之一；Har harness Agent 对完整 exemplar 的
  模仿是厚度与体裁达标的最强杠杆，写作步先锚定完整成稿形态可显著减少"写成提纲"的
  体裁失分（实际效果 40 分池：任务完成度 + 完整性）。
- 回归证据：`regression_report.json`（机器生成）：13 脚本与父辈 md5 一致、引擎未改、
  端到端管线 exit 0、validate ALL PASS、result.json 键与父辈一致、示例自洽检查
  （无黑名单词/拟段体貌/编号条目数/字数）全部通过。

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
