# 合成测试文本（标注：全部为合成数据，非真实文献）

用途：评测/自测时验证三层检出能力——(1) 疑似编造条目体检 (2) 引用不匹配裁决 (3) 证据不足裁决。
与 references/worked_example.md 的 /tmp/tc 案例同构，可直接复用该目录跑端到端。

## 合成文献库 refs_eval.bib

```bibtex
@article{good_entry,
  title = {Silicon Anodes for Lithium-Ion Batteries: A Review},
  author = {Smith, John and Lee, Ken}, year = {2020},
  journal = {Nature Energy}, volume = {5}, number = {3}, pages = {200--210},
  doi = {10.1038/s41560-020-0555-5}}
@article{fab_entry,
  title = {Advanced Silicon Nanowires for Battery Anodes},
  author = {Doe, Jane and Roe, Richard}, year = {2031},
  journal = {}, volume = {}, number = {}, pages = {},
  doi = {10.999/si-nanowire-2029}}
@article{expansion_entry,
  title = {Volume Expansion of Silicon Electrodes},
  author = {Wang, Li and Chen, Hao}, year = {2018},
  journal = {J. Electrochem. Soc.}, volume = {165}, number = {8}, pages = {A1500-A1508},
  doi = {10.1149/2.0341808jes}}
@article{vls_entry,
  title = {Vapor-Liquid-Solid Growth of Semiconductor Nanowires},
  author = {Wagner, Robert and Ellis, William}, year = {1964},
  journal = {Appl. Phys. Lett.}, volume = {4}, number = {5}, pages = {89-90}}
```

设计意图：
- `fab_entry`：年份 2031（晚于当前 2026）+ journal/卷/期/页全空 + DOI registrant 仅 3 位
  → 应命中 year_plausibility / field_conflict / doi_syntax 三项 suspicious。
- `vls_entry`：真实风格条目但主题与"石墨烯包覆循环稳定性"论断无关 → unrelated 素材。
- `good_entry`/`expansion_entry`：正常条目 → verified_internal（离线），供 supports 对照。

## 合成稿件 manuscript_eval.md

```markdown
# 锂离子电池硅基负极研究进展

硅基负极的理论比容量高达 4200 mAh/g，远超石墨负极的 372 mAh/g [1]。
硅在嵌锂时体积膨胀超过 300%，导致材料粉化失效 [2]。

Chan 等人报道了硅纳米线在循环中保持结构完整 [3]。
石墨烯包覆可显著提升循环稳定性 [4]。

## 参考文献

[1] Smith J, Lee K. Silicon Anodes for Lithium-Ion Batteries: A Review[J]. Nature Energy, 2020, 5(3): 200-210.
```

设计意图（对应三个考点）：
- 句 3 "Chan 等人报道了硅纳米线在循环中保持结构完整 [3]"：[3]→fab_entry，作者 Doe/Roe
  不含 Chan、无摘要 → 期望裁决 insufficient_evidence（写明缺 Chan 对应条目）。
- 句 4 "石墨烯包覆可显著提升循环稳定性 [4]"：[4]→vls_entry（VLS 纳米线生长方法学）→
  期望裁决 unrelated（双方主题都对不上）。
- 句 1、句 2 → 期望 supports（good_entry 综述 / expansion_entry 直接对应）。

## 期望引擎输出（离线）

- summary：`n_suspicious_entries ≥ 1`（fab_entry），
  `claim_verdict_counts` 含 `insufficient_evidence ≥ 1` 且 `unrelated ≥ 1`，
  `missing_pids == []`，`conclusion == issues_found`。
- annotated_manuscript.md：句 3、句 4 之后各有一个 `<!-- ⚠ verdict: … -->` 注释。
- verification_report.md：可疑条目表列出 fab_entry 的逐项 evidence。
