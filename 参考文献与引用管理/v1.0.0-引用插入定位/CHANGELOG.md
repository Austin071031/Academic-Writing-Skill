# CHANGELOG

## v1.0.0 (2026-11-19)

- 首次发布。核心能力：论断级（句子级）引用定位与插入。
- 新增专属引擎 `scripts/place_citations.py`：
  - 三级句子定位（精确 / 空白宽容 / 去空白映射），失败记 exceptions 并跳过、不臆造插入；
  - 论断句末（终结标点之前）插入 numeric `[n,m]` 或著者-出版年 `(作者, 年)` 标记；
  - 同句多引合并为单标记（连续区间压缩），多句一引展开为同号多标记；
  - 按首次出现顺序全局重排 1..N，调用 cite_engine 按引用顺序渲染 references.md；
  - 默认剥除旧标记并按 decisions 重放（全程 change_log）；旧参考文献段落默认移除；
  - placement_audit.json：段末 30 字符错放疑似（原稿观察 + 插入后自检）、
    一句多引合并校验、多句一引展开统计。
- 配套文档：claim_rubric.md（论断判定细则 + 10 正反例）、placement_rules.md、
  worked_example.md（合成示例端到端）、failure_modes.md（8 类基础 Agent 典型失败与对策）、
  evaluation/scoring_sheet.md（100 分制）、evaluation/test_texts.md（3 段合成测试文本）。
- 端到端自测（合成案例 SYNTH-01）：5 条 decisions（含 1 条故意失败）→ 插入 4 标记、
  编号 1-5 连续、异常 1 条如实记录，validate_output.py PASS。
