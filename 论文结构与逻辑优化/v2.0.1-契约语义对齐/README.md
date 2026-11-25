# section-narrative-flow（章节结构与叙事顺序）v2.0.1

论文结构与逻辑优化 Skill：**主攻章节结构与叙事顺序**，六维普查兜底覆盖。

> **v2.0.1 单点迭代**（父辈 v1.0.1 / attempt 89588 / 66.00 分）：新增契约逐字段语义对齐——`contract_check.py` 把 case.json 的 output_contract 逐字段与产物职责描述做关键词重叠打分（中文二字组/英文词），生成 `work/contract_map.json`（mapped_artifact/score/justification/coverage），`assemble_result.py` 据此将每个契约字段回填为 `{artifact, summary, coverage}` 语义结构（missing 自动登记 uncertainty），`validate_output.py` 校验契约字段非 null 且带 coverage 标记，解决 v1 评审口径"Solid — refine for a more complete and rigorous solution"中契约字段被固定 alias 表笼统映射、语义不符即填错或填 None 的缺口。其余资产与父辈逐字节一致（见 regression_report.json）。

## 它解决什么问题

基础 Agent 审稿件结构时给出的大多是"建议调整章节顺序"这类笼统意见。本技能把叙事顺序做成**可机检的序列与占比表**：

- **角色序列逆序对**：逐节归类角色（引言/方法/结果/讨论/结论…），与规范论证序比对，列出全部逆序对（结果先于方法、结论先于结果、参考文献不在末尾），逐条给出移动建议；
- **核心章节缺失**：引言/方法/结果（或实验）/结论缺环即 high 级断裂；全文仅 1-2 节自动降级为提示；
- **篇幅表**：单节占比 >55% → 拆分候选；方法章 <8% 且结果章存在 → "方法过薄"；引言 >35% → "铺垫过长"；
- **信息释放顺序**：缩写首现未定义、"如前所述"类回指无前文对应，逐句定位；
- **重组大纲草稿**（restructured_outline.md）：现状序列 → 建议叙事顺序，各节去向 + move/merge/split/add 汇总，作者直接对照执行。

每条问题定位到 **章节 › 段落 › 句子** 并附原文锚点与 9 类编辑动作之一（move/merge/split/narrow/qualify/add/add_transition/add_limitation/reorder），输出**编辑计划而非改写稿**。

## 快速开始

```bash
# 平台环境（/input 有 case.json/task.md/稿件）
python3 scripts/init_result.py
python3 scripts/inspect_case.py --work /app/work
python3 scripts/parse_manuscript.py --work /app/work
python3 scripts/six_scan.py --work /app/work
python3 scripts/section_flow.py --work /app/work
python3 scripts/report_builder.py --work /app/work --out /app/output \
  --focus section_structure --skill "section-narrative-flow v2.0.1"
python3 scripts/contract_check.py --case /input/case.json --work /app/work --out /app/output
# → 人工/Agent 复核 diagnosis_report.md（删误报/补漏报/定优先级）
# → 阅读 work/contract_map.json：missing 字段补产物或在 uncertainty 说明
python3 scripts/assemble_result.py --work /app/work --out /app/output \
  --skill "section-narrative-flow v2.0.1" --status success
python3 scripts/validate_output.py --out /app/output --work /app/work
```

完整说明见 [docs/USAGE.md](docs/USAGE.md)；最小调用示例见 [examples/minimal_example.md](examples/minimal_example.md)。

## 目录

- `SKILL.md` — 技能本体（Agent 工作流）
- `scripts/` — 纯标准库 Python3 管线（零依赖；PDF 抽取可选依赖 pdftotext）
- `references/` — 判据、分类、标注示例、误报模式
- `docs/USAGE.md` — 使用与方法说明、失败处理、自查
- `evaluation/` — 评分自查表、合成测试文本
- `examples/` — 最小调用示例（示意输出已标注）

## 兼容与限制

Python ≥ 3.8，无第三方依赖；稿件格式 md/txt/tex/docx/pdf。阈值集中于 `scripts/scanutil.py:THRESH`，可复核可调。角色归类依赖标题关键词，刁钻标题会归入 other 而漏检，需人工复核（见 references/failure_modes.md）。
