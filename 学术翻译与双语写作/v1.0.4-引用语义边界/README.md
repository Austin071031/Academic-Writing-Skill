# citation-semantic-boundary v1.0.4

学术翻译 Skill（引用保留与语义边界方向）：引用/语气双索引（译前）→ 受约束翻译 →
逐句段比对（引用标记多重集、参考文献条目完整性、否定/限定/强度迁移、增译数字）
+ ⚠ 标注稿，保证“边界清”——引用归属完整、否定范围不丢、语气强度不漂移、
不出现作者没说过的结论。

## 安装

自包含 Skill；平台安装为 `/skills/weekly-skill` 后按 `SKILL.md` 执行。
本地复现仅需 Python 3.8+ 标准库（PDF 可选 `pdftotext`）。

## 快速开始

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output; mkdir -p $W $O
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
python3 $S/boundary_engine.py index --work $W
# Agent：对照 citation_index 翻译 → work/translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/boundary_engine.py audit --work $W
# Agent：复核修订后重跑上两步
python3 $S/report_builder.py --work $W --out $O --focus boundary --skill "citation-semantic-boundary v1.0.4"
python3 $S/assemble_result.py --work $W --out $O --skill "citation-semantic-boundary v1.0.4" --status success
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、稿件（md/txt/tex/docx/pdf）。
- 输出：`translation_full.md`、`bilingual.md`、`citation_index.json`、
  `boundary_audit.json`、`audit_annotated.md`、`report.md`、`result.json` 等。

## 边界

- 语气核对基于可扩展词表；句式承担的否定/限定由 Agent 复核。
- 引文-论断语义相关性核验不在本版本范围。

## 仓库与维护

- GitHub：<https://github.com/Austin071031/Academic-Writing-Skill>（`学术翻译与双语写作/v1.0.4-引用语义边界/`）
- 变更历史见 `CHANGELOG.md`。
