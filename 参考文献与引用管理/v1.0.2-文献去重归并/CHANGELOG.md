# CHANGELOG

## v3.0.0（2026-11-19）

- 初始版本：可解释多信号文献去重与条目归并。
- 新增专属脚本 `dedup_engine.py`：
  - `candidates`：题名归一化（小写/去标点/去 [J][C][EB/OL] 类型标记/去
    "a review·综述"等价后缀/去 arXiv 标记）+ CJK 与 Latin 字符 3-gram Jaccard
    题名相似度；六信号（title_sim/doi_match/year_diff/author_overlap/venue_sim/
    type_compatible）；三档处置（auto_merge / needs_review / protected）；
    保护对冲突边跳过；跨语言同译提示（cross_language_hint）。
  - `apply`：Agent 裁决执行、字段择优与并集补全、冲突差异说明、arXiv 号进
    extra_fields.arxiv_id、保护对硬校验、library_deduped.json / merge_report.md /
    work/merge_report.json / work/dedup_mapping.json（rid+编号映射，匹配失败
    如实记 limits）。
- 复制 8 个共享核心脚本（接口未改动）。
- 文档：SKILL.md（Phase 0-5 逐字命令 + 裁决规则 + 红线 + 异常表 + 预算兜底）、
  references/（dedup_criteria、field_reconciliation、worked_example、failure_modes）、
  evaluation/（scoring_sheet、test_texts）、docs/USAGE.md、examples/minimal_example.md。
- 合成案例端到端自测通过：5 条 → 2 条（si_review 三形式合一、ris 期刊/会议合一），
  validate PASS，preview.html 生成。
