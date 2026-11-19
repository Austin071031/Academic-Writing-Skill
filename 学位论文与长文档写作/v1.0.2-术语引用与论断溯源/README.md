# longdoc-citation-trace v1.0.2

学位论文与长文档写作周赛（challenge-32c0210d）参赛 Skill，方向【术语与引用、论断溯源（查得清）】。

## 能力概览

- **论断-文献绑定**：每条含引用标记的段落抽为论断记录，按 numeric / author_year / latex /
  footnote_md 四种样式解析到文献库条目；未命中即 unbound（critical）——
  直接回答"引用了不存在的文献"。
- **论断-材料核验**：论断句数值与材料逐值核对（verbatim / derived ±1% 含百分比换算 /
  unverified），遮蔽图表号、章节号、年份、化学式内嵌数字。
- **语气边界审查**：论文语气阶梯（证明>表明>显示>可能）与材料原句比对，检出升格
  （overstated）与否定翻转（negation_flip）——直接回答"引用了文献但结论被改写"。
- **漏引发现**：含未溯源事实数值却无引用标记的段落，按关键词重叠推荐 top3 候选条目。
- **GB/T 7714-2015 文献表**：顺序编码渲染 + 正文编号连续性、双向一致交叉核对。
- **术语缩写统一**：判据驱动的 Agent 检查流程（references/citation_rules.md §5）。
- **⚠ 批注稿**：不改正文，在存疑处插入审校批注，供作者裁决。

## 目录结构

```
SKILL.md                  技能定义（Phase 0-5 流程、红线、异常处置表）
scripts/
  trace_engine.py         本版本引擎：bind / verify / render_refs / annotate
  init_result.py          共享：防超时空手的 result.json 骨架
  inspect_case.py         共享：输入盘点
  parse_chapters.py       共享：分章解析 → chapters.json（含 cite_marks）
  parse_library.py        共享：多格式文献库 → library.json
  cite_engine.py          共享：引用渲染/重排/转换/一致性 audit
  assemble_result.py      共享：汇总 result.json
  validate_output.py      共享：交付闸门
  render_previews.py      共享：HTML 预览
references/citation_rules.md   判据（与引擎一致）
references/failure_modes.md    12 类典型失败模式
docs/USAGE.md                  用法与中间产物格式
examples/minimal_example.md    端到端标注示例
evaluation/scoring_sheet.md    评分对齐自评
evaluation/test_texts.md       合成测试文本与预期
```

## 快速开始

见 docs/USAGE.md 与 examples/minimal_example.md。端到端合成测试结果见
evaluation/test_texts.md（负例三类缺陷全部检出、正例零误报、validate_output PASS）。
