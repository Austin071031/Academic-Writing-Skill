# CHANGELOG

## v2.0.0（2026-11-25）复核闭环主通道

- 父辈：v1.0.1-章节结构叙事（attempt 89588，66.00 分，本题五方向最高分）。
- 单点改动（唯一一件事）：新增 `scripts/review_helper.py`（pack/apply 两命令）+ SKILL.md 第 7 步重构为带预算表的逐条裁决协议（采纳/修正/驳回+理由、总体诊断、维度主问题判定），裁决结论回写报告 0.5 节。
- 提分假设：v1 评审口径"more complete and rigorous"——实际效果 40 分中 Agent 判断层未充分落地；本改动把复核从"建议"升级为"强制闭环"，且以 review_pack 一次成文控制模型预算（≤12 请求完成全流程）。
- 资产守恒：父辈 9 个脚本 md5 不变（见 regression_report.json），仅新增 1 个脚本与文档更新。
- 回归：合成案例 8 步+pack/apply 全通，validate PASS；驳回/修正/总体诊断回写正确。

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
