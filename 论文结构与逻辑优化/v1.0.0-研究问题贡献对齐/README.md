# rq-contribution-alignment（研究问题与贡献主张对齐）v1.0.0

论文结构与逻辑优化 Skill：**主攻研究问题（RQ）与贡献主张对齐**，六维普查兜底覆盖。

## 它解决什么问题

基础 Agent 审稿件结构时给出的大多是通用写作原则。本技能把"问题—方法—结果—结论"闭环做成**可机检的映射**：

- RQ×章节覆盖矩阵：每个研究问题在方法/实验/结果/讨论/结论章的内容词覆盖率，低于阈值即"无承接/无回应"候选；
- 贡献×证据映射：每条贡献主张与含数据/图表锚点段落的最大重叠，三档裁决（supported / weak / unsupported）；
- 首尾呼应矩阵：摘要与引言中的论断句在结论中的回声相似度，列出"承诺未兑现"。

每条问题定位到 **章节 › 段落 › 句子** 并附原文锚点与 9 类编辑动作之一（move/merge/split/narrow/qualify/add/add_transition/add_limitation/reorder），输出**编辑计划而非改写稿**。

## 快速开始

```bash
# 平台环境（/input 有 case.json/task.md/稿件）
python3 scripts/init_result.py
python3 scripts/inspect_case.py --work /app/work
python3 scripts/parse_manuscript.py --work /app/work
python3 scripts/six_scan.py --work /app/work
python3 scripts/rq_engine.py --work /app/work
python3 scripts/report_builder.py --work /app/work --out /app/output \
  --focus research_question --skill "rq-contribution-alignment v1.0.0"
# → 人工/Agent 复核 diagnosis_report.md（删误报/补漏报/定优先级）
python3 scripts/assemble_result.py --work /app/work --out /app/output \
  --skill "rq-contribution-alignment v1.0.0" --status success
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

Python ≥ 3.8，无第三方依赖；稿件格式 md/txt/tex/docx/pdf。阈值集中于 `scripts/scanutil.py:THRESH`，可复核可调。同义改写导致的漏配需人工复核（见 references/failure_modes.md）。
