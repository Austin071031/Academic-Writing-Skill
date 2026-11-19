# Minimal Example（示例，非正式案例结果）

## 输入：一个 4 条文献库（含一条同名不同文陷阱）

`library.bib`：

```bibtex
@article{a_formal,
  title  = {Graphene-Based Supercapacitors: A Review},
  author = {Liu, Yang and Wang, Fang},
  year   = {2022}, journal = {Adv. Mater.},
  volume = {34}, number = {12}, pages = {210123},
  doi    = {10.1002/adma.20210123}
}
@misc{a_preprint,
  title  = {Graphene-Based Supercapacitors: A Review},
  author = {Liu, Yang and Wang, Fang},
  year   = {2021}, eprint = {2110.01234}, note = {arXiv preprint}
}
@article{trap_same_name,
  title  = {Graphene Oxide Membranes for Water Desalination},
  author = {Liu, Yang}, year = {2022},
  journal = {J. Membr. Sci.}, volume = {648},
  doi = {10.1016/j.memsci.2022.12045}
}
@article{field_gaps,
  title  = {Graphene-Based Supercapacitors: A Review},
  author = {Liu, Yang and Wang, Fang},
  year   = {2022}, journal = {Adv. Mater.},
  doi = {10.1002/adma.20210123}
}
```

（第 1、2、4 条为同一文献的期刊版/预印本/缺卷期导出；第 3 条是同名作者 Liu Yang
的不同研究，属陷阱。）

## 调用

```bash
python3 /skills/weekly-skill/scripts/parse_library.py library.bib --work /app/work
python3 /skills/weekly-skill/scripts/dedup_engine.py candidates --library /app/work/library.json --work /app/work
```

示意输出（信号为示意值）：

```
[candidates] 扫描 6 对，候选 6 对，组 1 个（自动合并 1），保护对 2，未入组 1 条
G001 auto_merge [R001, R002, R004]
  R001~R002 title_sim=1.0 author_overlap=1.0 year_diff=1 type_compatible=preprint_formal
  R001~R004 doi_match=True
protected: R001~R003 / R002~R003（两个不同 DOI 均存在且不相同；同作者同年 title_sim<0.60）
ungrouped: R003
```

Agent 写 work/merge_decisions.jsonl：

```json
{"group_id":"G001","action":"merge","keep_rid":"R001","drop_rids":["R002","R004"],"rationale":"R001~R002 title_sim=1.0、author_overlap=1.0、year_diff=1（预印本↔正式版正常）；R001~R004 doi_match=True；字段互缺互补。保留正式期刊版，arXiv 2110.01234 进 extra_fields.arxiv_id。"}
```

```bash
python3 /skills/weekly-skill/scripts/dedup_engine.py apply --library /app/work/library.json --decisions /app/work/merge_decisions.jsonl --work /app/work --out /app/output
# [apply] 4 -> 2 条；合并 1 组；分立 0 组；异常 0
python3 /skills/weekly-skill/scripts/cite_engine.py render --records /app/output/library_deduped.json --style gbt2015_numeric --out /app/output/references.md
```

## 示意输出（references.md）

```
## 参考文献

[1] Liu, Yang, Wang, Fang. Graphene-Based Supercapacitors: A Review[J]. Adv. Mater., 2022, 34(12): 210123. DOI: 10.1002/adma.20210123.

[2] Liu, Yang. Graphene Oxide Membranes for Water Desalination[J]. J. Membr. Sci., 2022, 648. DOI: 10.1016/j.memsci.2022.12045.
```

merge_report.md 中 G001 含完整信号表、字段来源（volume/pages 来自 R001，缺的由
R004 无冲突补齐）与差异说明（year 2022 vs 2021、eprint 保留说明）；R003 因
protected 未被合并，独立保留为 [2]。
