# 合成测试文本（全部为合成数据，非真实文献）

> 用途：开发自查。覆盖：中英混排、缺页码条目、会议论文条目、同题重复条目（字段互补正例）、
> 缺 DOI 条目、4 作者截断。

## T1：mixed.bib（中英混排 + 缺页码 + 会议 + 重复对）

```bibtex
@article{en_full,
  title = {Silicon Anodes for Lithium-Ion Batteries: A Review},
  author = {Smith, John and Lee, Ken and Brown, Amy and Clark, Zoe},
  year = {2020},
  journal = {Nature Energy},
  volume = {5},
  number = {3},
  pages = {200--210},
  doi = {10.1038/s41560-020-0555-5}
}
@article{cn_nopages,
  title = {锂离子电池硅负极研究进展},
  author = {张三 and 李四 and 王五 and 赵六},
  year = {2021},
  journal = {储能科学与技术},
  volume = {10},
  number = {4}
}
@inproceedings{conf_en,
  title = {Volume Expansion of Silicon Electrodes},
  author = {Wang, Li and Chen, Hao},
  year = {2018},
  booktitle = {Proceedings of the National Electrochemistry Conference},
  pages = {15--20}
}
@article{dup_a,
  title = {Graphene Composite Anodes},
  author = {Liu, Wei},
  year = {2019},
  journal = {Carbon},
  volume = {150},
  pages = {1--9},
  doi = {10.1016/j.carbon.2019.05.001}
}
@article{dup_b,
  title = {Graphene Composite Anodes},
  author = {Liu, Wei},
  year = {2019},
  journal = {Carbon}
}
```

预期：

- R002（cn_nopages）：中文全角；4 作者 → `张三, 李四, 王五, 等`；`missing_fields=["pages","doi"]` → `not_provided`。
- R003（conf_en）：类型标识 `[C]`；`missing_fields` 含 `volume/issue/doi`。
- R004/R005（同题同年同类型重复对）：R005 的 volume/pages/doi 被互补，
  动作 `copied_from_R004`（source_rid=R004），其余缺失仍 `not_provided`。
- R001：4 作者英文 → `Smith J, Lee K, Brown A, et al`。

## T2：mixed.ris（RIS 回转测试输入）

```ris
TY  - JOUR
AU  - Wang, Li
AU  - Chen, Hao
TI  - Volume Expansion of Silicon Electrodes
JO  - J. Electrochem. Soc.
PY  - 2018
VL  - 165
IS  - 8
SP  - A1500
EP  - A1508
DO  - 10.1149/2.0341808jes
ER  -
TY  - CONF
AU  - 王五
AU  - 李雷
TI  - 硅电极体积膨胀的原位观测
T2  - 全国电化学会议论文集
PY  - 2019
ER  -
```

预期：第 2 条中文会议 → `[C]`、`missing_fields` 含 `volume/issue/pages/doi`；
`--to ris` 回转输出中 TY - CONF、AU 逐行、缺字段行不出现（不臆造）。

## T3：style_probe.md（任务书措辞 → 目标规范）

| 任务书措辞 | 预期 --to |
|---|---|
| "按 GB/T 7714-2015 顺序编码制整理" | gbt2015_numeric |
| "改为国标著者-出版年制" | gbt2015_author |
| "format references in APA 7th" | apa7 |
| "Vancouver style (ICMJE)" | vancouver |
| "导出为 bibtex 与 ris" | bibtex / ris 各跑一次 |
