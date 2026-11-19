# Worked Example：端到端合成案例（/tmp/tc/input）

以下为合成教学案例（SYNTH-V5，非正式评测案例），演示 Phase 0–5 全流程与预期输出。

## 合成输入

`/tmp/tc/input/case.json`：

```json
{"case_id": "SYNTH-V5", "output_contract": {"result": null, "evidence": null, "changes": null, "status": null}}
```

`/tmp/tc/input/manuscript.md`：

```markdown
# 锂离子电池硅基负极研究进展

硅基负极的理论比容量高达 4200 mAh/g，远超石墨负极的 372 mAh/g [1]。
硅在嵌锂时体积膨胀超过 300%，导致材料粉化失效 [2]。

Chan 等人报道了硅纳米线在循环中保持结构完整 [3]。
石墨烯包覆可显著提升循环稳定性 [4]。

## 参考文献

[1] Smith J, Lee K. Silicon Anodes for Lithium-Ion Batteries: A Review[J]. Nature Energy, 2020, 5(3): 200-210.
```

`/tmp/tc/input/refs.bib`（4 条，含 1 条疑似编造）：

```bibtex
@article{si_review,
  title = {Silicon Anodes for Lithium-Ion Batteries: A Review},
  author = {Smith, John and Lee, Ken}, year = {2020},
  journal = {Nature Energy}, volume = {5}, number = {3}, pages = {200--210},
  doi = {10.1038/s41560-020-0555-5}}
@article{fake_entry,
  title = {Advanced Silicon Nanowires for Battery Anodes},
  author = {Doe, Jane and Roe, Richard}, year = {2031},
  journal = {}, volume = {}, number = {}, pages = {},
  doi = {10.999/si-nanowire-2029}}
@article{volume_expansion,
  title = {Volume Expansion of Silicon Electrodes},
  author = {Wang, Li and Chen, Hao}, year = {2018},
  journal = {J. Electrochem. Soc.}, volume = {165}, number = {8}, pages = {A1500-A1508},
  doi = {10.1149/2.0341808jes}}
@article{nanowire_growth,
  title = {Vapor-Liquid-Solid Growth of Semiconductor Nanowires},
  author = {Wagner, Robert and Ellis, William}, year = {1964},
  journal = {Appl. Phys. Lett.}, volume = {4}, number = {5}, pages = {89-90}}
```

## 关键设定

- R002 `fake_entry`：年份 2031（晚于当前 2026）→ year_plausibility suspicious；
  journal/volume/number/pages 全空且类型 journal_article → field_conflict suspicious；
  DOI `10.999/…` registrant 仅 3 位 → doi_syntax suspicious。三条同时命中 = 高度疑似编造。
- 论断句"石墨烯包覆可显著提升循环稳定性 [4]"：R004 是 1964 年 VLS 纳米线生长方法学论文，
  主题为纳米线生长而非石墨烯包覆/循环稳定性 → 裁决 unrelated（引用不匹配）。
- 论断句"Chan 等人报道了硅纳米线在循环中保持结构完整 [3]"：R002 作者 Doe/Roe 不含 Chan，
  且其真实性本身可疑；材料内无摘要可确认"循环中保持结构完整" → insufficient_evidence
  （缺作者 Chan 对应条目；R002 仅有题名可粗略相关但证据不足）。

## Agent 写的 work/match_verdicts.jsonl（覆盖 2 个正文段落，每句一行）

```jsonl
{"pid": "P002", "sentence": "硅基负极的理论比容量高达 4200 mAh/g，远超石墨负极的 372 mAh/g", "entry_ids": ["R001"], "verdict": "supports", "rationale": "条目题名 'Silicon Anodes for Lithium-Ion Batteries: A Review' 为硅负极综述，可支撑'理论比容量4200 mAh/g'的领域共识性数值"}
{"pid": "P002", "sentence": "硅在嵌锂时体积膨胀超过 300%，导致材料粉化失效", "entry_ids": ["R003"], "verdict": "supports", "rationale": "条目题名 'Volume Expansion of Silicon Electrodes' 与论断'体积膨胀超过300%'直接对应"}
{"pid": "P003", "sentence": "Chan 等人报道了硅纳米线在循环中保持结构完整", "entry_ids": ["R002"], "verdict": "insufficient_evidence", "rationale": "论断点名 'Chan 等人'，但 R002 作者为 'Doe, Jane; Roe, Richard' 且条目无摘要；缺：Chan 对应的文献条目"}
{"pid": "P003", "sentence": "石墨烯包覆可显著提升循环稳定性", "entry_ids": ["R004"], "verdict": "unrelated", "rationale": "论断主题为'石墨烯包覆提升循环稳定性'，而 R004 题名 'Vapor-Liquid-Solid Growth of Semiconductor Nanowires' 是纳米线生长方法学，主题对不上"}
```

## 引擎输出要点（离线模式）

- `verification_report.json` → `summary`：
  `n_entries=4, n_suspicious_entries=1`（R002），
  `claim_verdict_counts={supports:2, insufficient_evidence:1, unrelated:1}`，
  `missing_pids=[]`（两个正文段落全覆盖），`conclusion=issues_found`。
- 联网状态（离线）：有合法 DOI 的 R001/R003 → `not_attempted_offline_mode`；
  R002 DOI 语法不通过 → `online_skipped_invalid_doi`；R004 无 DOI → `online_skipped_no_doi`。
- `annotated_manuscript.md`：第 3 段两句后分别出现
  `<!-- ⚠ verdict: insufficient_evidence | entries: R002 | rationale: ... -->` 与
  `<!-- ⚠ verdict: unrelated | entries: R004 | rationale: ... -->`；其余原文不动。
- `verification_report.md`：可疑条目表列出 R002 三行体检证据；不匹配论断表列出 unrelated 句；
  证据不足清单列出 Chan 句；编号一致性节（nrefs=文献库条数 4）给出越界/缺口/样式混杂结论，
  本例正文标记 [1]–[4] 均在 1..4 内 → 无越界、无缺口、样式一致。

## 加 --online 时

R001、R003 的 DOI 会请求 Crossref：命中且题名相似度 ≥0.8 → `verified_online`；
网络不可用 → `unverified_offline`（如实，不影响其余产物）。
