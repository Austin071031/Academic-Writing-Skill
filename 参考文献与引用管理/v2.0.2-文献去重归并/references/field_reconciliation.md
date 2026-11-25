# 字段择优与冲突处理规则（合并执行）

`dedup_engine.py apply` 按本规则执行字段归并，全程留痕于 merge_report.md
（保留字段来源）与差异说明。

## 1. keep_rid 的选择

优先级从高到低：
1. **正式版 > 预印本**：entry_type ∈ {journal_article, conference_paper, book,
   book_chapter, thesis, report, standard, patent} 优先于 {preprint, misc}；
2. **字段更全者优先**：title/authors/year/venue/volume/issue/pages/doi 八个字段
   中已填数量多者；
3. 同档取 id 较小者（解析顺序靠前）。

Agent 可在裁决中显式指定 keep_rid 覆盖（如指定保留中语正式版），
引擎校验其属于该组，否则回退自动择优并记异常。

## 2. 字段并集补全

对每个核心字段（title, authors, year, entry_type, venue, volume, issue,
pages, doi, language）：
- keep 有值 → 用 keep 值，来源记 keep_rid；
- keep 缺失而某 drop 有值 → 用该 drop 值补全，来源记该 drop_rid；
- 全部缺失 → 记 None。
merge_report.md 的"保留字段来源"一节逐字段记录取值来源 rid，可审计。

## 3. 冲突字段处置

- **冲突定义**：keep 与 drop 对同一字段均有值且不同（如年份 2020 vs 2019、
  卷 5 vs 9、刊名 Nature Energy vs 储能科学与技术）。
- **处置原则**：以 keep 为准（与 keep_rid 择优逻辑一致），被并条目的取值
  全部写入差异说明，格式：`字段冲突[字段]：以 keep(<rid>)=<值> 为准；被并条目取值：<rid>=<值>；…`。
- 预印本与正式版年份不同属正常（投稿/上线年份差），同样按上述规则记录，
  但 rationale 中应注明"年份差为预印本↔正式版正常现象"。

## 4. extra_fields 与特殊字段

- extra_fields 做并集：keep 已有的键不被覆盖，drop 独有的键并入并标注来源；
- **arXiv 号保护**：drop 条目 extra_fields.eprint（或 arxiv_id）必须写入
  keep 的 extra_fields.arxiv_id，差异说明中记录原 rid；禁止丢失；
- drop 条目的原始记录仍保留在 work/library.json 与 merge_report.json 的
  merged_from / dropped 列表中，可完整回溯。

## 5. 溯源与可审计性

合并后条目带 `merged_from: [keep_rid, drop_rid...]`；library_deduped.json
含 source_count / dropped / merged_groups；merge_report.json 为机读全量
（signals、field_sources、diff_notes、rationale）。任何字段都可定位到
来源 rid 与裁决理由。

## 6. 禁止事项

- 禁止凭空补值（如推断卷期、编造 DOI）；
- 禁止静默丢弃 drop 条目的 DOI/页码——凡取值不一致必入差异说明；
- 禁止合并后丢失 language 信息：冲突时以 keep 为准，但另一语种题名/刊名
  至少保留在差异说明中。
