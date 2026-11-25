# CHANGELOG

## v2.0.3（2026-11-25）增益自证卡

- 父辈：v1.0.1-章节结构叙事（attempt 89588，66.00 分，本题五方向最高分）。
- 单点改动（唯一一件事）：新增 `scripts/gain_card.py`（纯标准库，report_builder 之后、assemble_result 之前运行）——从 findings.json/stats.json/change_log.json/diagnosis_report.md 机器可复算地计算六维覆盖率、原文锚点率、可执行动作率、定位粒度分布、机械劳动清单（脚本步骤 vs Agent 判断步骤）与估计效率（人工基线 n_chars/1500 字/分钟，注明"估计"），生成 gain_card.md/json 与反事实对照表（基础 Agent 通用建议示意 vs 本技能 high 级前 5 条摘录），并在 diagnosis_report.md 末尾追加"增益自证卡（机器可复算）"节（幂等）；`assemble_result.py` 仅 ARTIFACTS 列表增加 gain_card.md/json 一行。
- 提分假设：评分细则"使用增益 25 分（质量增益 15 + 效率增益 5 + 增益可验证 5）"与"创新增益 15 分"要求证明相对基础 Agent 的增量，而 v1 只交付诊断结果、未自证增益；本改动把增益做成机器可复算的自我审计，不虚构数字。
- 资产守恒：父辈 8 个脚本 md5 不变（见 regression_report.json），assemble_result.py 仅 ARTIFACTS 一行补丁，仅新增 1 个脚本与文档更新。
- 回归：合成案例 synthetic-struct-01 全管线（含 gain_card）跑通，validate PASS；gain_card.json 指标与 findings.json 手工复算一致；result.json outputs 含 gain_card。

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
