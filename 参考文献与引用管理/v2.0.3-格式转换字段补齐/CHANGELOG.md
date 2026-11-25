# CHANGELOG

## v2.0.3（2026-11-25）

- **唯一机制增量**（父版 v1.0.3-格式转换字段补齐，attempt 89252，49 分）：全自动单命令：本方向判断环节为零，把目标规范识别（task.md 关键词→四种规范）也脚本化，彻底消除流程未走完的失分点；附 bibtex/ris 回转导出。
- 新增 `scripts/run_pipeline.py` 编排器；引擎与共享核心判据与父版一致，未改动。
- SKILL.md 重写为三步/单命令快轨流程；docs/USAGE.md 增补快轨说明。


## v4.0.0 (2026-11-19)

- 首版。新增 `scripts/convert_engine.py`：
  - 调用共享内核 cite_engine render/convert 生成 converted_refs.txt / references.md；
  - field_audit.json 逐条字段审计（`copied_from_Rxxx` / `not_provided`）；
  - convert_report.md 人读报告（源格式统计→前后对照→字段保留率→未提供清单）；
  - 标点规范化（英文半角/中文全角，DOI 保护）；
  - 作者名 `Smith, John`→`Smith J`，不臆造中间名；
  - 类型标识表与规范参数改为运行时解析 `references/format_specs/*.md`；
  - `--try-online` Crossref 探测（5s 超时，失败记 unverified，不自动补值）。
- 新增 references/format_specs/ 四个规范数据文件 + gbt_type_tags.md；
  references/ 增加 punctuation_rules.md / worked_example.md / failure_modes.md。
- 共享核心 8 脚本原样复制，接口未改。
