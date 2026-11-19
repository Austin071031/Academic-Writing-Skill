# longdoc-consistency（学位论文与长文档写作 · 跨章节一致性维护 v1.0.1）

## 用途
维护长文档跨章节一致性（题面「连得上」）：术语/缩写/符号全文统一、图表公式交叉引用
双向核对与编号连续性、跨章结论矛盾候选、单点改动的受影响段落清单（影响面分析）。
引擎给候选与判据，Agent 做审定与裁决——不自动判错、不臆造定义。

## 安装与调用
平台将本目录安装为 `/skills/weekly-skill` 后由 Agent 按 `SKILL.md` 的 Phase 0-5 执行。
本地试用：

```bash
python3 scripts/parse_chapters.py ch1.md ch2.md --work work
python3 scripts/consistency_engine.py scan --chapters work/chapters.json --work work
# 审定 work/glossary_candidates.json → 写 work/glossary_review.json
python3 scripts/consistency_engine.py glossary --chapters work/chapters.json \
  --review work/glossary_review.json --work work
python3 scripts/consistency_engine.py impact --chapters work/chapters.json \
  --glossary work/glossary.md --changed-term "固态电解质" --work work
```

## 依赖
Python 3.8+ 标准库（consistency_engine.py 零第三方依赖）；docx/pdf 材料解析沿用
shared-core 的 zipfile / pdftotext 降级策略。

## 产物
术语表 `glossary.md`、一致性报告 `consistency_report.{json,md}`（逐处异写 pid+原文、
异写率、符号冲突）、交叉引用审计 `xref_audit.json`（dangling/unreferenced/编号）、
矛盾候选 `contradiction_candidates.json`、影响面 `impact_report.{json,md}`。

## 边界与已知限制
- 结论句矛盾检测是字面 n-gram + 否定词启发式：只出候选，语义改写型矛盾会漏，
  必须 Agent 人工裁决（见 references/failure_modes.md）。
- 高频复合词可能混入套话，需 Agent 在 glossary_review 中 `keep=false` 剔除。
- 图表编号 `3-1`/`3.1`/`3–1` 归一视为同一目标；刻意混用两套编号需先统一。
- 跨章比对按文件划分；单文件多章稿件退化为全文比对（stats 记录 single_chapter）。
- 影响面传播只有一跳；二阶影响可对结果段落再次运行 impact。

## 与其他版本关系
章节规划与篇幅论证问题（立得住）见 v1.0.0 目录；本目录只覆盖一致性方向。
