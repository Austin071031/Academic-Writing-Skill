# translation-number-fidelity v1.0.1

学术翻译 Skill（事实与数字方向）：数字台账（译前）→ 受约束翻译 → 逐句段双向数值比对
（译后），保证“数字实”——值、单位、量级、有效数字原样落地，万/亿↔million/billion
只允许等值换算。

## 安装

自包含 Skill；平台安装为 `/skills/weekly-skill` 后按 `SKILL.md` 执行。
本地复现仅需 Python 3.8+ 标准库（PDF 可选 `pdftotext`）。

## 快速开始

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output; mkdir -p $W $O
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
python3 $S/number_engine.py ledger --work $W
# Agent：对照 number_ledger 翻译 → work/translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/number_engine.py audit --work $W
# Agent：复核修订后重跑上两步
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "translation-number-fidelity v1.0.1"
python3 $S/assemble_result.py --work $W --out $O --skill "translation-number-fidelity v1.0.1" --status success
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、稿件（md/txt/tex/docx/pdf）。
- 输出：`translation_full.md`、`bilingual.md`、`number_ledger.json`、`number_audit.json`、
  `report.md`、`result.json` 等。

## 边界

- 中文大写数字、罗马数字、分数拼写不纳入机检（列入 uncertainty 人工核对）。
- 引擎核对“与原文一致”，不判断数值本身的科学合理性。

## 仓库与维护

- GitHub：<https://github.com/Austin071031/Academic-Writing-Skill>（`学术翻译与双语写作/v1.0.1-数字单位忠实/`）
- 变更历史见 `CHANGELOG.md`。
