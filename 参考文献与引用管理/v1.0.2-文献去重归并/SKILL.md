---
name: ref-dedup-merge
description: 文献去重与条目归并（收得净）。当任务要求对文献库/参考文献表去重、合并同一文献的多个版本（中英文题名、预印本与正式版、期刊版与会议版、不同数据库导出差异）并给出可解释合并依据时触发；不适用于撰写新引文、校对引用编号连续性（那是v1.0.1）或核验文献真实性（v1.0.4）。产出：去重后的文献库 library_deduped.json、合并报告 merge_report.md（每组合并的判据信号表+保留字段来源+差异说明）、merge_report.json、GB/T 7714 参考文献表 references.md、编号映射 dedup_mapping.json、result.json。
---

# v1.0.2｜文献去重与条目归并（收得净）

## 能力概述

对解析后的文献库（work/library.json）做**可解释的多信号去重**：
引擎为每条记录对计算成对相似信号（题名归一化相似度、DOI 一致、年份差、
作者姓氏重合、刊会相似、类型兼容度），分三档处置：

- **auto_merge 自动合并**：doi_match，或 title_sim≥0.90 且 author_overlap≥0.5 且 year_diff≤1；
- **needs_review 候选交 Agent 裁决**：其余有合并潜质的对（含跨语言同译提示对）——
  Agent 必须**逐组**给出 `merge` 或 `keep_separate` 裁决与理由，不得跳过；
- **protected 禁止合并保护**：两个不同 DOI 均存在且不相同；或同语种、同一第一作者、
  同一年但 title_sim<0.60（疑似同名不同文）。保护对不得被任何候选边连入同一组，
  apply 阶段对裁决再设硬校验，杜绝误合并同名作者的不同文献。

每个合并决定都附带完整证据信号表、字段来源溯源与差异说明（merge_report.md）。

## 三条红线

1. **不臆造文献、不臆造元数据**：只归并输入文献库中真实存在的条目；
   缺失字段只能并集补全，不得编造 DOI/卷期/页码。
2. **不臆造核验结果**：跨语言相似度不可比（comparable=false）就如实标注，
   由 Agent 依据 references/dedup_criteria.md 判据裁决，不得假装算出了相似度。
3. **合并必须走引擎**：禁止手工改 library.json 或正文编号；所有合并经
   dedup_engine.py apply 执行，编号重排后续必须走 cite_engine renumber。

## 阶段流程（Phase 0-5）

以下命令一律用绝对路径 `python3 /skills/weekly-skill/scripts/xxx.py`。
SKILL_DIR=/skills/weekly-skill。

### Phase 0 — 骨架与巡检（防超时空手）

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
```

Agent 读 `work/inspection.json`：确认 case_id、文献库候选文件清单（library_candidates）
与稿件候选（manuscript_candidates）。无文献库候选 → 记 exceptions.json，跳到 Phase 4 交付 partial。

### Phase 1 — 解析文献库（与稿件）

```bash
python3 /skills/weekly-skill/scripts/parse_library.py <文献库文件...> --work /app/work
# 若 inspection.json 有稿件候选：
python3 /skills/weekly-skill/scripts/parse_manuscript.py <稿件文件> --work /app/work
```

Agent 读 `work/library.json` 的 `issues`：有解析失败文件 → 记 exceptions.json；
`count==0` → 记异常，跳 Phase 4 交付 partial。

### Phase 2 — 生成候选对与信号

```bash
python3 /skills/weekly-skill/scripts/dedup_engine.py candidates --library /app/work/library.json --work /app/work
```

Agent 逐组读 `work/merge_candidates.json`：
- `groups[]`：每组 `tier`、`records`、`pair_signals`（每对 title_sim/doi_match/
  year_diff/author_overlap/venue_sim/type_compatible）与 `engine_reasons`；
- `protected_pairs` / `skipped_edges`：禁止合并的硬约束；
- `ungrouped_records`：未入组条目（无需裁决）。

### Phase 3 — Agent 逐组裁决（核心判断，不得跳过任何候选组）

Agent 依据 `references/dedup_criteria.md` 对**每个** group 写一行 JSONL 到
`work/merge_decisions.jsonl`：

```json
{"group_id":"G001","action":"merge","keep_rid":"R001","drop_rids":["R002","R003"],"rationale":"引用具体信号值与判据条款的完整理由"}
{"group_id":"G002","action":"keep_separate","keep_rid":null,"drop_rids":[],"rationale":"同名同姓但题名主题/作者组合/DOI 均不同，判为不同文献"}
```

裁决规则（与 dedup_criteria.md 对齐）：
- **同名同姓不同研究必须 keep_separate**：第一作者相同+同年但题名主题差异明显、
  作者组合不同、或 DOI 不同——任一成立即不得合并。
- **中英文同译合并**：comparable=false 但 author_overlap≥0.5 且年份接近的跨语言对，
  主题一致即可合并；保留语言信息更全/正式版为 keep。
- **预印本与正式版合并**：保留正式版（期刊/会议信息），预印本的 arXiv 号
  必须进 keep 条目的 `extra_fields.arxiv_id`；期刊↔会议（type_compatible=cautious）
  需主题、作者、年份均一致才合并，且 keep 正式期刊版。
- 引擎判 auto_merge 的组仍须 Agent 复核确认（写 merge 行并引用信号）；
  缺裁决的组 apply 时按 keep_separate 处理并记异常。

### Phase 4 — 执行合并与渲染

```bash
python3 /skills/weekly-skill/scripts/dedup_engine.py apply --library /app/work/library.json --decisions /app/work/merge_decisions.jsonl --work /app/work --out /app/output --manuscript /app/work/manuscript.json
python3 /skills/weekly-skill/scripts/cite_engine.py render --records /app/output/library_deduped.json --style gbt2015_numeric --out /app/output/references.md
```

Agent 读 `/app/output/merge_report.md` 校验：每组有信号表、字段来源、差异说明；
`work/dedup_mapping.json` 给出 drop→keep 的 rid/编号映射（编号映射依赖稿件参考
文献表与条目按题名匹配，失败时仅 rid 映射并在 limits 中说明）。
随后写 work/ 下的 evidence_map.json（每组合并的证据信号与裁决理由）、
change_log.json（merge 操作）、uncertainty.json、manual_confirmations.json、
exceptions.json（缺则写空数组/对象）、stats.json。

### Phase 5 — 组装、校验、预览

```bash
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --skill "ref-dedup-merge v3.0.0" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work --expect-status success
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output --work /app/work
```

若 validate FAIL：修复或如实降级 `--status partial` 重跑 assemble+validate。

## 异常处置表

| 异常 | 处置 |
|---|---|
| 文献库为空/解析 0 条 | exceptions.json 记录；Phase 4 交付 partial（无合并可执行） |
| 部分文件解析失败 | issues 记入 exceptions.json，对成功解析部分继续去重 |
| 字段缺失（无年份/无作者） | year_diff/author_overlap 记 None，降权为 needs_review，不臆造 |
| DOI 缺失或格式异常 | doi_match=False；仅一条有 DOI 不构成保护，两条不同 DOI 触发保护 |
| 条目歧义（跨语言对） | comparable=false 如实标注，交 Agent 按同译判据裁决 |
| 候选组未被裁决 | apply 按 keep_separate 保守处理并记异常（Agent 必须逐组裁决） |
| 裁决违反保护对 | apply 硬校验拒绝该组合并、记异常、keep_separate |
| 稿件参考文献表与条目匹配失败 | dedup_mapping.json 仅给 rid 映射，limits 说明 |
| 不支持的稿件格式/文件损坏 | parse_manuscript 降级，dedup_mapping 仅 rid 映射 |
| 超时（预算过半未完成 Phase 3） | 立即以已有候选+空裁决跑 Phase 4-5，全部组记 keep_separate(undecided)，交付 partial |

## 预算兜底

若模型请求过半仍未完成 Phase 3：停止剩余裁决，直接跑 Phase 4
（apply 对未裁决组自动 keep_separate 并记异常）与 Phase 5，`--status partial`，
在 result.json 的 stats/uncertainty 中说明未裁决组清单。
