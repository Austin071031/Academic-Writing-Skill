# bilingual-alignment-guard v1.0.2

学术翻译 Skill（双语对齐方向）：对齐计划 + 结构不变量（译前）→ 逐句段翻译 →
全覆盖核对（缺译/未知 ID/长度异常/图表编号与脚注集合一致性）→ 段首带 〔PID〕 的
双语对照稿，译者可逐段修改而不破坏结构。

## 安装

自包含 Skill；平台安装为 `/skills/weekly-skill` 后按 `SKILL.md` 执行。
本地复现仅需 Python 3.8+ 标准库（PDF 可选 `pdftotext`）。

## 快速开始

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output; mkdir -p $W $O
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
python3 $S/align_engine.py plan --work $W
# Agent：逐句段翻译 → work/translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/align_engine.py audit --work $W --out $O
# Agent：复核修订后重跑上两步
python3 $S/report_builder.py --work $W --out $O --focus alignment --skill "bilingual-alignment-guard v1.0.2"
python3 $S/assemble_result.py --work $W --out $O --skill "bilingual-alignment-guard v1.0.2" --status success
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、稿件（md/txt/tex/docx/pdf）。
- 输出：`bilingual.md`、`translation_full.md`、`alignment.json`、`align_audit.json`、
  `report.md`、`result.json` 等。

## 边界

- 长度比例为启发式，疑似漏译/增译需 Agent 复核定性。
- 图片内文字与扫描版 PDF 不纳入对齐（uncertainty 标注）。

## 仓库与维护

- GitHub：<https://github.com/Austin071031/Academic-Writing-Skill>（`学术翻译与双语写作/v1.0.2-双语句段对齐/`）
- 变更历史见 `CHANGELOG.md`。
