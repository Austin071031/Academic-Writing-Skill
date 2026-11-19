# translation-terminology-lock v1.0.0

学术翻译 Skill（术语一致性方向）：机选术语候选 → Agent 审定锁定术语表 → 句段级翻译 →
脚本逐句段核对术语合规，保证“术语稳”——同一术语在摘要、正文、图表题注、脚注中同一译法。

## 安装

本目录为自包含 Skill：平台将其安装为 `/skills/weekly-skill` 后按 `SKILL.md` 工作流执行。
本地复现仅需 Python 3.8+ 标准库（PDF 输入可选依赖 `pdftotext`）。

## 快速开始

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output; mkdir -p $W $O
python3 $S/init_result.py
python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W
python3 $S/segment_builder.py --work $W
python3 $S/term_engine.py seed --work $W
# Agent：审定 work/glossary_seed.json → work/glossary.json；分批翻译 → work/translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/term_engine.py audit --work $W
# Agent：复核修订后重跑上两步
python3 $S/report_builder.py --work $W --out $O --focus terminology --skill "translation-terminology-lock v1.0.0"
python3 $S/assemble_result.py --work $W --out $O --skill "translation-terminology-lock v1.0.0" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、稿件（md/txt/tex/docx/pdf）。
- 输出：`/app/output/translation_full.md`（纯译文）、`bilingual.md`（双语对照）、
  `glossary.json`（锁定术语表）、`term_audit.json`、`report.md`、`result.json` 等。

## 边界

- 术语候选为统计抽取，低频无缩写术语可能漏选（Agent 可手工补充 glossary）。
- 机检核对译名使用一致性，不判断译名学科正确性（由 Agent 审定环节保证）。
- 详尽的异常与降级策略见 `SKILL.md` 异常处理表与 `docs/USAGE.md`。

## 仓库与维护

- GitHub：<https://github.com/Austin071031/Academic-Writing-Skill>（`学术翻译与双语写作/v1.0.0-术语一致性锁定/`）
- 变更历史见 `CHANGELOG.md`；问题排查见 `references/failure_modes.md`。
