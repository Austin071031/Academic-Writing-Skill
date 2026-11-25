# CHANGELOG

## v2.0.2（2026-11-25）改后对照预览

- 父辈：v1.0.1-章节结构叙事（attempt 89588，66.00 分，本题五方向最高分；五版得分 63.67–66.00，评审口径 "Solid — refine for a more complete and rigorous solution."）。
- 单点改动（唯一一件事）：新增 `scripts/apply_preview.py`（纯标准库，report_builder 之后运行的独立后处理，不改 report_builder）——为每条 finding（上限 12 条，high 优先）生成"改前/改后对照预览"：before=原文锚点 quote/段落 snippet，after=按 op（narrow/qualify/add/add_transition/add_limitation/move/merge/split/reorder）的确定性模板生成的建议示例文本，统一标注"建议示例（非最终文本）"，不新增材料外事实；对照注入 diagnosis_report.md 每个 finding 块末尾（改前/改后两行）与 edit_plan.json 每个 op 的 preview 字段，并落盘 work/previews.json。脚本幂等，Agent 第 7 步复核增删 findings 后重跑即可刷新。
- 提分假设：题面"改得动"要求输出可执行编辑动作，v1 已给 op+instruction 但仍是文字指令，作者需自行想象改后形态；对照预览让改得动/任务完成度/质量增益可直观核验。
- 资产守恒：父辈 9 个脚本 md5 不变（见 regression_report.json），仅新增 1 个脚本与文档更新（SKILL.md 工作流 6.5 步、输出物清单、限制节；README 引用块；docs/USAGE.md）。
- 回归：合成案例 synthetic-struct-01 全管线（含 apply_preview）跑通，validate PASS；"结论数字无出处(narrow)""绝对化表述(qualify)"finding 均获得改前/改后对照，报告注入行与 edit_plan preview 字段核验存在；全部脚本 py_compile 通过。

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
