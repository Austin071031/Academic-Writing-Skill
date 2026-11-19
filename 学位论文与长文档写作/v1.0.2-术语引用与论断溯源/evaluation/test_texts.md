# 合成测试文本（test_texts.md）

> 全部为人工合成的演示文本（标注：合成），与真实文献无关；任何相似纯属巧合。
> 测试数据位于 `../../_test/input/`，运行痕迹在 `../../_test/work3/`、`output3/`。
> 请勿修改 `_test/work/` 与 `_test/output/`（v1.0.0 版本测试产物）。

## 输入（合成）

| 文件 | 内容 |
|-|-|
| `input/chapters/ch1_intro.md` | 正例稿：numeric 引用 [1][2]；「电导率可达 3.2 mS/cm」论断；研究目标句「5.0 mS/cm 以上」（预期豁免） |
| `input/ch1_bad.md` | 负例稿（合成）：`[5]` 越界 + `9.9 mS/cm` 材料无值 + 「完全解决……问题」升格 |
| `input/materials/refs.bib` | 合成 bibtex 2 条：zhang2023sse、wang2022interface |
| `input/materials/facts.md` | 合成实验事实：450°C/2 h、520°C/1 h、3.2 mS/cm、5.8 mS/cm、40%、批次 B7 |
| `input/materials/notes_interface.md` | 合成调研笔记：界面稳定性仍是关键挑战，可能缓解 |

## 用例 1：正例（零误报）

命令链：parse_chapters(ch1_intro) → parse_library(refs.bib) →
materials_all.txt = facts.md + notes_interface.md → bind → verify。

预期（实际运行结果）：
- bind：论断 1 条，bound=1（[1]→R001，[2]→R002）；
- verify：`unbound=0 unverified=0 tone=0 missing_cite=0`，exit 0；
- 3.2 mS/cm → verbatim；目标句「5.0 mS/cm 以上」豁免；「Li6PS5Cl」数字遮蔽；
  「第1章」「[1][2]」遮蔽。

## 用例 2：负例（三类缺陷全部检出）

命令链：parse_chapters(ch1_bad) --out-name chapters_bad.json → verify。

预期（实际运行结果）：
- (a) `numeric [5] 越界（文献表仅 2 条）` severity=critical，exit 1；
- (b) `数值 9.9 unverified`；
- (c) `overstated+negation_flip: 论文 L4 vs 材料 L1`（材料句「仍是关键挑战……可能缓解」）；
- annotate：3 条批注全部定位（定位 3，未定位 0）。

## 用例 3：author_year / latex 绑定回归

合成稿（标注：合成）：
```
研究表明……（Zhang, 2023），……（Zhang 等, 2023）。
另有工作（Wang, 2022），以及不存在的引用（Li, 1999）。
\cite{zhang2023sse} 报告了固态电池综述，\cite{nonexist2024} 不存在。
```
预期（实际运行结果）：P001 bound→R001（两条 author_year 同时命中）；
P002 partially_bound（Li 1999 未命中）；P003 partially_bound（nonexist2024 未命中）。
> 修复记录：`norm_surname` 原先对「Zhang 等」含 CJK 误入中文分支，v1.0.2 已修复
> （先剥离等/et al 再判断语种）。

## 用例 4：端到端交付（validate_output PASS）

命令链：正例 verify 清零 → render_refs（默认 order=正文出现序）→
copies revised 稿/chapter_1.md + citation_audit.md + references.md 至 output3 →
assemble_result --status success → validate_output --expect-status success →
render_previews。

预期（实际运行结果）：
- render_refs：2 条，out_of_range=[] gaps=[] sequential=true；
- validate：`PASS (status=success)`；preview.html 覆盖 3 个 md 产物。

## 用例 5：交付闸门自检

references.md 与含 `[5]` 的 annotated_draft.md 若同进 output →
validate 报「正文引用了文献表中不存在的编号」→ 按 failure_modes F10 处置
（references 暂不出 output 或降级 partial）。此用例用于验证闸门有效性，
运行时不落盘到 output3。
