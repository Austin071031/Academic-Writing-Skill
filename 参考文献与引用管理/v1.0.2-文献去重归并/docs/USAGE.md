# USAGE：完整调用步骤、输入输出与自查方法

## 1. 运行环境契约

- 输入：`/input/case.json` + `/input/task.md` + 材料（文献库 bib/ris/enw/ciw/csv/json/
  GB-T 文本；稿件 md/txt/tex/docx/pdf 可选）。
- 工作目录 `/app/work`，产物 `/app/output`（必须含 result.json）。
- 仅 Python3 标准库；脚本承担全部机械劳动，Agent 只做 Phase 3 的逐组裁决。

## 2. 完整调用步骤（与 SKILL.md Phase 0-5 一一对应）

```bash
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_library.py /input/<refs.bib> /input/<refs.ris> ... --work /app/work
python3 $S/parse_manuscript.py /input/<manuscript.md> --work /app/work   # 有稿件时
python3 $S/dedup_engine.py candidates --library /app/work/library.json --work /app/work
# —— Agent 在这里读 work/merge_candidates.json，逐组写 work/merge_decisions.jsonl ——
python3 $S/dedup_engine.py apply --library /app/work/library.json --decisions /app/work/merge_decisions.jsonl --work /app/work --out /app/output --manuscript /app/work/manuscript.json
python3 $S/cite_engine.py render --records /app/output/library_deduped.json --style gbt2015_numeric --out /app/output/references.md
# —— Agent 写 work/evidence_map.json、change_log.json、uncertainty.json、
#    manual_confirmations.json、exceptions.json、stats.json ——
python3 $S/assemble_result.py --work /app/work --out /app/output --skill "ref-dedup-merge v3.0.0" --status success
python3 $S/validate_output.py --out /app/output --work /app/work --expect-status success
python3 $S/render_previews.py --out /app/output --work /app/work
```

merge_decisions.jsonl 每行格式（候选组必须逐组裁决，不得跳过）：

```json
{"group_id":"G001","action":"merge","keep_rid":"R001","drop_rids":["R002"],"rationale":"引用信号值与 dedup_criteria.md 判据的完整理由"}
{"group_id":"G002","action":"keep_separate","keep_rid":null,"drop_rids":[],"rationale":"同名同姓不同研究/不同 DOI/主题差异，依据 dedup_criteria.md §3"}
```

## 3. 输入输出对照

| 输入 | 中间（work/） | 输出（/app/output） |
|---|---|---|
| 文献库文件 | library.json | library_deduped.json |
| — | merge_candidates.json（候选组+信号明细） | — |
| Agent 裁决 | merge_decisions.jsonl | — |
| — | merge_report.json、dedup_mapping.json | merge_report.md、references.md(+json) |
| case.json/task.md | inspection.json | result.json、preview.html(+status) |

## 4. 实测记录（合成案例 SYNTH-01，2026-11-19 实测）

测试方法：合成输入（3 条 BibTeX 三形式重复 + 2 条 RIS 期刊/会议版 + 稿件）
在临时目录按 §2 全流程跑通。关键命令输出：

```
[parse_library] refs.bib: 3 条 (bibtex)
[parse_library] refs_ris.ris: 2 条 (ris)
[parse_library] 共 5 条 -> work/library.json
[candidates] 扫描 10 对，候选 5 对，组 2 个（自动合并 0），保护对 1，未入组 0 条
[apply] 5 -> 2 条；合并 2 组；分立 0 组；异常 0；编号映射 已写
[render] 2 条, 样式 gbt2015_numeric -> /app/output/references.md
[assemble] status=success outputs=['references', 'merge_report', 'library_deduped']
[validate] PASS (status=success)
[render_previews] preview.html 已生成
```

实测信号值（work/merge_candidates.json）：

| 对 | title_sim | doi_match | year_diff | author_overlap | venue_sim | type_compatible |
|---|---|---|---|---|---|---|
| R001~R002（英↔中） | 0.0（跨语言不可比） | False | 0 | 1.0 | 0.0 | same |
| R001~R003（期刊↔预印本） | **1.0** | False | 1 | 1.0 | 0.0 | preprint_formal |
| R002~R003（中↔预印本） | 0.0（跨语言不可比） | False | 1 | 1.0 | 0.0 | preprint_formal |
| R004~R005（期刊↔会议） | 0.0（跨语言不可比） | False | 0 | 1.0 | 0.0 | cautious |
| R001~R004（保护对） | — | —（两个不同 DOI） | — | — | — | — |

实测结论：
- si_review 组（R001/R002/R003）裁决 merge → 保留 R001，并入 R002/R003，
  arXiv 1912.00001 进入 extra_fields.arxiv_id；
- ris 组（R004/R005）裁决 merge → 保留 R004（期刊版），会议出处进差异说明；
- 5 → 2 条；merge_report.md 两组信号表完整；dedup_mapping.json rid 映射齐全，
  稿件 [1]（张三. 硅负极综述）与库不匹配 → number_mapping 为空并在 limits 说明；
- 同名作者陷阱单测：Zhang Wei 两篇不同 DOI 文献 → protected，未入组。

## 5. 自查方法

1. `validate_output.py` 必须 PASS；candidate/apply 打印的对数、组数与
   merge_report.md 一致。
2. 抽查 merge_report.md：每组都有信号表（6 个信号列齐全）、字段来源、差异说明；
   合并后条数 = 原始条数 − Σ(每组 drop 数)。
3. 核对 dedup_mapping.json：每个被 drop 的 rid 都有映射指向；number_mapping 为空时
   必须有 limits 解释。
4. library_deduped.json 中每个合并条目 merged_from 完整、arxiv_id 未丢、
   source_count/dropped 与报告一致。
5. references.md 编号从 [1] 连续（validate 会复检 references.json）。
