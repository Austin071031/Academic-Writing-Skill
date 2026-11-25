# translation-completion-guard v2.0.0

学术翻译 Skill（v2 迭代·完整率保障方向，父辈 v1.0.1）：批文件预切 + 进度追踪 +
预算告警，保证 64 请求/900 秒内整篇 100% 覆盖交付；保留父辈数字台账与双向比对。

## 安装

自包含 Skill；平台安装为 `/skills/weekly-skill` 后按 `SKILL.md` 执行。
本地复现仅需 Python 3.8+ 标准库（PDF 可选 `pdftotext`）。

## 快速开始

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output; mkdir -p $W $O
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
python3 $S/number_engine.py ledger --work $W
python3 $S/batch_planner.py plan --work $W --batch-size 15
# Agent 主循环：读批文件 → 翻译追加 translations.jsonl → status 查下一批/预算
python3 $S/batch_planner.py status --work $W --used-requests 10
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/number_engine.py audit --work $W
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "translation-completion-guard v2.0.0"
python3 $S/assemble_result.py --work $W --out $O --skill "translation-completion-guard v2.0.0" --status success
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、稿件（md/txt/tex/docx/pdf）。
- 输出：`translation_full.md`、`bilingual.md`、`progress.json`、`number_ledger.json`、
  `number_audit.json`、`report.md`、`result.json` 等。

## 边界

- 预算告警依赖 Agent 自报已用请求数；批量工程不改翻译质量本身（由数字机检+复核保证）。

## 仓库与维护

- GitHub：<https://github.com/Austin071031/Academic-Writing-Skill>（`学术翻译与双语写作/v2.0.0-批量进度与完整率保障/`）
- 变更历史见 `CHANGELOG.md`（含 v1.0.1 评分基线）。
