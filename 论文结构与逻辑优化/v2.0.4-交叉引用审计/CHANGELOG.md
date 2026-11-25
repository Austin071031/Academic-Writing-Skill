# CHANGELOG

## v2.0.4（2026-11-25）交叉引用审计

- 父辈：v1.0.1-章节结构叙事（attempt 89588，66.00 分，本题五方向最高分）。
- 单点改动（唯一一件事）：`scripts/section_flow.py` 新增 **xref_audit 交叉引用完整性审计**——
  - 引用侧（正文句子，排除参考文献章）提取 图/表/Fig/Table、式/公式/Eq、第N章节/Section、`[n]` 文献引用（区间展开）；
  - 定义侧锚点：独立图注段（单句段、编号后随非数字文本或冒号、无句末标点）、段末 `(n)`/`\tag{n}` 公式锚点、标题数字编号、参考文献条目计数；
  - 悬空（high，add："补定义或修正编号"）：图表/公式/章节/文献四类；文献条目未被引用（medium，narrow："删除或在正文补引"）；图表编号跳号（low，reorder 提示）；
  - xref 类 findings dimension=argument_chain，与原有类合并后按 severity 稳定截断 ≤15 条；
  - `section_map.json` 新增 `xref_audit` 键（引用侧/定义侧统计、悬空清单、skipped 说明、method_note）；打印行尾部追加 `xref: figrefs=a dangling=b citerefs=c dangling=d uncited=e`；
  - 无参考文献表 / 标题无数字编号时对应审计项自动跳过并在 `xref_audit.skipped` 注明（防误报）。
- 提分假设：评分细则"结果正确性"要求不漏真实断裂、题面"链得通"要求跨章节呼应成立；"见图3 无图3""引用[5] 文献表仅 4 条""条目从未被引"是真实稿件高频硬伤，v1 引擎完全不覆盖。
- 资产守恒：其余 8 个脚本 md5 与父辈一致（见 regression_report.json），section_flow.py 标注 patched。
- 回归：T3 合成稿（evaluation/test_texts.md）四类悬空+未引用+跳号全命中、validate PASS；/tmp/w05test/input "图1 显示循环曲线"（引用无定义）命中图表引用悬空、无新误报、validate PASS。
- 文档：SKILL.md（frontmatter/第 5 步/输出物清单/异常表）、references 三件（structure_rules 第 8 节、taxonomy XR-A…F、failure_modes 新增 6 行）、README、CHANGELOG、GITHUB_URL.txt、docs/USAGE.md、examples/minimal_example.md 同步更新。

## v1.0.1（2026-11-19）

- 基于 v1.0.0 共享管线派生，主攻维度切换为"章节结构与叙事顺序"（section-narrative-flow）。
- 新增主攻引擎 `section_flow.py`：
  - 章节角色序列与规范叙事序比对，枚举全部逆序对（结果先于方法、结论先于结果、参考文献不在末尾等）；
  - 核心章节缺失检测（引言/方法/结果或实验/结论），全文仅 1-2 节自动降级、综述文体按 genre 豁免；
  - 篇幅分析（单节 >55% 拆分、方法 <8% 且存在结果章报"方法过薄"、引言 >35% 报"铺垫过长"）；
  - 标题层级跳变、同级同名标题（合并候选）、空章节检测；
  - 信息释放顺序：缩写首现未定义（全称（ABBR）/ABBR（全称）模式核验）、"如前所述/aforementioned"回指无前文对应；
  - 结果/结论章大段方法性描述后移候选。
- 新增产物：`section_map.json`（角色序列表/篇幅表/缩写表）与 `restructured_outline.md`（现状序列→建议叙事顺序+动作汇总草稿）。
- references 改写：structure_rules.md（角色/顺序/篇幅/缩写判据）、section_taxonomy.md（SS-A…SS-J 分类）、worked_example.md、failure_modes.md。
- 交付物扩展：diagnosis_report.md / edit_plan.json / findings.json / section_map.json / restructured_outline.md / result.json（契约字段回填）。
- 异常路径 9 类：新增"全文仅 1-2 节降级"与"综述文体豁免"。

## v1.0.0（2026-11-19）

- 共享核心管线首版：init_result / inspect_case / parse_manuscript / six_scan / report_builder / assemble_result / validate_output（纯标准库）。
- 六维轻量普查：研究问题/章节结构/论证链/段落关系/重复内容/结论边界。

维护：阈值集中于 scripts/scanutil.py THRESH 与 section_flow.py 顶部常量；新增误报模式请登记 references/failure_modes.md。
