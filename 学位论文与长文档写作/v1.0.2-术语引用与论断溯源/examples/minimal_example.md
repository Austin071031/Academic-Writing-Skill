# 最小端到端示例（标注版）

输入（合成，见 evaluation/test_texts.md）：

- 稿件 `ch1_bad.md`：

```markdown
# 第1章 绪论（负例：含三类引用缺陷）

已有研究证明，Li6PS5Cl 的电导率可达 9.9 mS/cm [5]。

两步烧结法完全解决了硫化物固态电解质的界面稳定性问题 [1]。
```

- 文献库 `refs.bib`：仅 2 条（zhang2023sse、wang2022interface）。
- 材料 `materials_all.txt`：facts.md（含「基准样品电导率 3.2 mS/cm」）+
  调研笔记（含「界面稳定性仍是关键挑战，现有包覆方法可能缓解」）。

## 第一步 bind

```
[bind] 论断 2 条: bound=1 partially_bound=0 unbound=1
  [unbound] C01-S001-P001: numeric [5] 越界（文献表仅 2 条）
```

→ `claim_bindings.json`：P001 status=unbound（**critical：引用了不存在的文献**），
P002 bound→R001。

## 第二步 verify

`citation_audit.md` 关键内容（实际引擎输出）：

```
- (a) 引用存在性问题: 1 处（critical）
- (b) 数值核对: verbatim=0 derived=0 unverified=1
- (c) 语气边界候选: 1 处

## (a) 引用存在性（critical）
- ⚠ [C01-S001-P001] numeric [5] 越界（文献表仅 2 条）

## (b) 论断-材料数值一致性
- ⚠ [C01-S001-P001] 数值 9.9 unverified：材料中未找到该数值或可推导关系

## (c) 语气边界候选（供 Agent 裁决）
- ⚠ [C01-S001-P002] overstated+negation_flip: 论文语气 L4 vs 材料语气 L1
  - 论断: 两步烧结法完全解决了硫化物固态电解质的界面稳定性问题 [1]。
  - 材料: - Wang 等报道……界面稳定性仍是关键挑战，现有包覆方法可能缓解副反应。
```

三类缺陷——不存在的引用、被改写的结论、臆造的数值——全部显式标出。

## 第三步 Agent 裁决（change_log 节选）

```json
[{"op": "replace", "location": "P001", "before": "可达 9.9 mS/cm [5]",
  "after": "可达 3.2 mS/cm [1]",
  "reason": "[5] 越界（unbound）+ 9.9 unverified；材料基准值为 3.2 mS/cm，对应文献 R001"},
 {"op": "replace", "location": "P002", "before": "完全解决了……界面稳定性问题",
  "after": "缓解了……界面稳定性问题",
  "reason": "材料原文为『仍是关键挑战/可能缓解』，论文升格为 L4，降回 L1 同级"}]
```

## 第四步 annotate（作者审阅版，正文不动）

```markdown
已有研究证明，Li6PS5Cl 的电导率可达 9.9 mS/cm [5]。
> ⚠ 审校批注（trace_engine）：引用存在性: numeric [5] 越界（文献表仅 2 条）（critical）
> ⚠ 审校批注（trace_engine）：数值 9.9 未在材料中溯源（unverified）
```

## 第五步 复核 + render_refs + 交付

修订稿重跑 verify：`unbound=0 unverified=0 tone=0` → 清零；
`render_refs` 生成 GB/T 7714-2015 文献表（[1] Zhang…[2] Wang…），
交叉核对 `out_of_range=[] gaps=[] sequential=true`；
`validate_output` PASS，`render_previews` 生成 preview.html。

## 反例（正稿零误报）

稿件 `ch1_intro.md`（`电导率可达 3.2 mS/cm [1]`、`界面稳定性仍是关键挑战 [2]`、
目标句「提升至 5.0 mS/cm 以上」）：
verify 输出 `unbound=0 unverified=0 tone=0 missing_cite=0`——
verbatim 数值不报、平实转述不报、研究目标句豁免、自有数据段不报漏引。
