# Worked Example：合成案例端到端走查（示例，非正式案例结果）

合成输入（与 evaluation/test_texts.md 的"三形式重复"用例同源，放在 /tmp 下自测）：

- `refs.bib` 三条：`si_review`（Nature Energy 2020 期刊版）、`si_review_cn`
  （储能科学与技术 2020 中文版）、`si_preprint`（arXiv 1912.00001, 2019）；
- `refs_ris.ris` 两条：Wang/Chen 的 J. Electrochem. Soc. 2018 期刊版与
  全国电化学会议 2018 会议版；
- `manuscript.md`：正文数字引用 + 一条与文献库匹配不上的参考文献 [1]。

## 步骤 1：解析

```bash
python3 scripts/parse_library.py refs.bib refs_ris.ris --work work
# [parse_library] refs.bib: 3 条 (bibtex) / refs_ris.ris: 2 条 (ris) / 共 5 条
python3 scripts/parse_manuscript.py manuscript.md --work work
```

## 步骤 2：候选生成

```bash
python3 scripts/dedup_engine.py candidates --library work/library.json --work work
# [candidates] 扫描 10 对，候选 5 对，组 2 个（自动合并 0），保护对 1，未入组 0 条
```

`work/merge_candidates.json` 关键内容（实测信号值）：

- **G001**（needs_review，R001/R002/R003）：
  - R001~R002：title_sim=0.0（跨语言不可比 comparable=false），author_overlap=1.0，
    year_diff=0，type_compatible=same —— 引擎理由"跨语言对但作者姓氏高度重合且年份
    接近：可能为同一文献的中/英文不同译名"；
  - R001~R003：title_sim=1.0，author_overlap=1.0，year_diff=1，
    type_compatible=preprint_formal；
  - R002~R003：跨语言不可比，author_overlap=1.0，year_diff=1；
- **G002**（needs_review，R004/R005）：title_sim=0.0（跨语言），author_overlap=1.0，
  year_diff=0，type_compatible=cautious（期刊↔会议）；
- **protected**：R001~R004（两个不同 DOI 均存在且不相同——本就是两篇不同文献，
  保护规则如实拦截）。

## 步骤 3：Agent 逐组裁决（work/merge_decisions.jsonl）

G001 → merge，keep R001（正式期刊版），drop R002/R003；理由引用判据
"中英文同译合并 + 预印本↔正式版合并"，注明 arXiv 1912.00001 进 extra_fields。
G002 → merge，keep R004（期刊版），drop R005；注明 cautious 档已核对主题/
作者/年份一致，会议出处记入差异说明。

## 步骤 4：执行合并与渲染

```bash
python3 scripts/dedup_engine.py apply --library work/library.json --decisions work/merge_decisions.jsonl --work work --out /app/output --manuscript work/manuscript.json
# [apply] 5 -> 2 条；合并 2 组；分立 0 组；异常 0；编号映射 已写
python3 scripts/cite_engine.py render --records /app/output/library_deduped.json --style gbt2015_numeric --out /app/output/references.md
# [render] 2 条, 样式 gbt2015_numeric
```

结果：
- `library_deduped.json`：2 条（R001 合并自 R001+R002+R003，extra_fields 含
  arxiv_id=1912.00001；R004 合并自 R004+R005）；
- `merge_report.md`：两组均含判据信号表（实测数值如上）、逐字段来源（全 R001 /
  全 R004，因 keep 字段最全）、差异说明（年份 2020vs2019、刊名、卷期页、语种等
  冲突逐条记录 + arXiv 号保留说明）；
- `work/dedup_mapping.json`：rid_mapping {R002→R001, R003→R001, R005→R004}；
  本例稿件参考文献 [1]（张三. 硅负极综述. 电化学 2019）与库中记录按题名匹配
  失败 → number_mapping 为空，limits 如实说明，供后续版本重排时参考。

## 步骤 5：组装校验

```bash
python3 scripts/assemble_result.py --work work --out /app/output --skill "ref-dedup-merge v3.0.0" --status success
python3 scripts/validate_output.py --out /app/output --expect-status success   # PASS
python3 scripts/render_previews.py --out /app/output                           # preview.html
```
