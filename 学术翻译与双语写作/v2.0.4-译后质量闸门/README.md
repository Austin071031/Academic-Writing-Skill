# translation-qa-gate v2.0.4

学术翻译 Skill（v2 迭代·译后质量闸门方向，父辈 v1.0.1）：qa_gate.py 一次三门
机检（数字忠实 + 引用/语义边界 + 缩写一致性），去重后按严重度排序出统一修复
清单，高严重度清零方可交付。

## 安装

自包含 Skill；平台安装为 `/skills/weekly-skill` 后按 `SKILL.md` 执行。
本地复现仅需 Python 3.8+ 标准库（PDF 可选 `pdftotext`）。

## 快速开始

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output; mkdir -p $W $O
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
python3 $S/number_engine.py ledger --work $W && python3 $S/boundary_engine.py index --work $W
# Agent 翻译 → translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/qa_gate.py --work $W      # 本版核心：三门机检 + 统一修复清单
# Agent 按 fix_list 修复后重跑上两步（高严重度清零）
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "translation-qa-gate v2.0.4"
python3 $S/assemble_result.py --work $W --out $O --skill "translation-qa-gate v2.0.4" --status success
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、稿件（md/txt/tex/docx/pdf）。
- 输出：译文/对照稿 + `qa_report.json`（统一修复清单）+ 各门审计文件 + `result.json`。

## 边界

- 词表可扩展（custom_lexicon.json）；闸门核对“与原文一致”，不判断原文科学正确性。

## 仓库与维护

- GitHub：<https://github.com/Austin071031/Academic-Writing-Skill>（`学术翻译与双语写作/v2.0.4-译后质量闸门/`）
- 变更历史见 `CHANGELOG.md`（含 v1.0.1 评分基线）。
