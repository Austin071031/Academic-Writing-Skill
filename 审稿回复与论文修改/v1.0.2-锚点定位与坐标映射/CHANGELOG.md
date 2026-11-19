# CHANGELOG

## v1.0.2（2026-11-19）

- 方向：锚点定位与坐标映射。在共享核心 8 脚本之上新增主攻引擎 anchor_engine.py。
- 双坐标定位：每个 applied op 同时给出基线侧（章节+段 ID+基线行号，逐行搜索 anchor_quote）与修订侧（修订稿行号+段 ID+新文本前 30 字）坐标；锚点找不到时标注"锚点已由改写消除"并附 method/ratio。
- 行级 diff 映射：difflib 行级对齐生成 change regions（基线行区间→修订稿行区间），op 按 revised_line 反查挂接；location_table.md 全表自动生成，Agent 不再手抄行号。
- 回复信定位声明核验：E# 引用必须在 applied 集合内；引号引文（≥8 字）必须在修订稿中逐字可检（或命中意见原文视为摘录）；P###/SEC#/第 N 行坐标必须合法；不可核对声明入 unresolvable_claims 并 exit 1。
- 失效锚点预警：fuzzy 命中 op 单列"人工复核定位"预警区。
- 文档：SKILL.md（八步工作流 + 13 类异常表）、anchor_rules.md（双坐标/引文/行号映射/失效锚规范）、location_table 模板、自查清单与评分对照表按定位方向重写。
- 本地合成案例端到端冒烟：5 op 全部双坐标、3 个变更区域；注入假引文/悬空 E#/越界行号均被 exit 1 检出，移除后 PASS；verify/validate PASS。

## v1.0.0（2026-11-19）

- 基线版本（方向一：意见拆解与覆盖台账），见同仓库 `审稿回复与论文修改/v1.0.0-意见拆解与覆盖台账`。本版本复用其共享核心脚本与文档骨架。
