# 合成测试文本（标注：全部为本 Skill 自造的合成数据，非真实文献）

用途：本地端到端自测 dedup_engine 的候选生成、Agent 裁决、合并执行与报告留痕。
每组用例给出输入要点与期望行为。

## T1 三形式重复（中英同译 + 预印本/期刊版）

合成条目（BibTeX，见 references/worked_example.md 全文）：
- si_review：*Silicon Anodes for Lithium-Ion Batteries: A Review*, Smith & Lee, 2020,
  Nature Energy, DOI 10.1038/s41560-020-0555-5（**合成 DOI**）；
- si_review_cn：《锂离子电池硅负极综述》, Smith & Lee, 2020, 储能科学与技术（合成）；
- si_preprint：同英文题名, 2019, arXiv 1912.00001（合成）。

**期望**：三条进同一候选组 G001（needs_review，含 cross_language_hint）；
R001~R003 title_sim=1.0；裁决 merge keep 正式版后 5→2 条中的第 1 条，
arxiv_id 保留在 extra_fields。

## T2 期刊版与会议版（跨语言同译，cautious 档）

合成 RIS 两条：Wang & Chen《Volume Expansion of Silicon Electrodes》
J. Electrochem. Soc. 2018, DOI 10.1149/2.0341808jes（合成）；《硅电极体积膨胀研究》
全国电化学会议 2018。

**期望**：候选组 G002（needs_review，type_compatible=cautious，跨语言不可比）；
裁决 merge keep 期刊版 R004；会议出处（全国电化学会议, 15-20）进差异说明。

## T3 同名不同文陷阱

合成条目：Zhang, Wei 2021《Deep Learning for Battery State of Estimation》
J. Power Sources, DOI 10.1016/j.jpowsour.2021.228（合成）；
Zhang, Wei 2021《Deep Learning for Catalyst Screening》Nat. Catal.,
DOI 10.1038/s41929-021-004（合成）；
加一条 Zhang, Wei & Liu, Na 2020 同题预印本 arXiv 2009.00002（合成）。

**期望**：两篇不同 DOI 的期刊论文 → protected（title_sim≈0.27），不并入任何组；
预印本与对应期刊版 → auto_merge 组 {期刊版, 预印本}；连接预印本与另一篇的
弱边被 skipped_edges 跳过；最终 3 条变 2 条，绝不 1 条。

## T4 字段互缺的互补条目

合成条目：同一 DOI 的两次导出，一条有 volume/issue 无 pages，另一条有 pages
无 volume/issue（合成 DOI 10.1002/adma.20210123）。

**期望**：doi_match=True → auto_merge；合并后 volume/issue/pages 全有，
字段来源逐字段记录（volume 来自 R001、pages 来自 R002），merge_report.md 可审计。

## T5 稿件编号映射（退化情形）

合成稿件：正文 [1-5] 引用 + 参考文献表，其中 [1]（张三. 硅负极综述[J]. 电化学, 2019）
与文献库任何条目按题名均匹配不上。

**期望**：dedup_mapping.json 输出 rid_mapping（R002→R001 等）与 new_order_rids；
number_mapping 为空并在 limits 中如实说明"稿件参考文献表条目与文献库记录未能
按题名匹配"——不得臆造编号映射。

## 自测命令（在临时目录）

```bash
python3 scripts/parse_library.py <T1.bib> <T2.ris> --work work
python3 scripts/dedup_engine.py candidates --library work/library.json --work work
# 手写 work/merge_decisions.jsonl 后：
python3 scripts/dedup_engine.py apply --library work/library.json --decisions work/merge_decisions.jsonl --work work --out out --manuscript work/manuscript.json
python3 scripts/cite_engine.py render --records out/library_deduped.json --style gbt2015_numeric --out out/references.md
```
