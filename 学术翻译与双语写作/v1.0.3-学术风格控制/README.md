# academic-style-control v1.0.3

学术翻译 Skill（学术风格方向）：翻译管线 + 译文语域/句式机检（直译痕迹四类 +
语域越界三类 + 长句分布 + 的/被密度指标），逐句段给出改写指令，Agent 修订后复检，
把直译腔拉回学术语域，同时守住克制语气。

## 安装

自包含 Skill；平台安装为 `/skills/weekly-skill` 后按 `SKILL.md` 执行。
本地复现仅需 Python 3.8+ 标准库（PDF 可选 `pdftotext`）。

## 快速开始

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output; mkdir -p $W $O
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
# Agent：按 style_rules 翻译 → work/translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/style_engine.py audit --work $W
# Agent：按改写指令修订后重跑上两步
python3 $S/report_builder.py --work $W --out $O --focus style --skill "academic-style-control v1.0.3"
python3 $S/assemble_result.py --work $W --out $O --skill "academic-style-control v1.0.3" --status success
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、稿件（md/txt/tex/docx/pdf）。
- 输出：`translation_full.md`、`bilingual.md`、`style_report.json`、`report.md`、
  `result.json` 等。

## 边界

- 规则库覆盖高频问题而非穷尽；机检不改写，文学性修订由 Agent 完成。
- 非中英目标语仅交付翻译产物（uncertainty 标注）。

## 仓库与维护

- GitHub：<https://github.com/Austin071031/Academic-Writing-Skill>（`学术翻译与双语写作/v1.0.3-学术风格控制/`）
- 变更历史见 `CHANGELOG.md`。
