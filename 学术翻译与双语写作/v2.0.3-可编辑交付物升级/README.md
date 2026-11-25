# editable-deliverables-plus v2.0.3

学术翻译 Skill（v2 迭代·可编辑交付物方向，父辈 v1.0.1）：纯标准库生成
translation.docx / bilingual.docx（可编辑 Word），LibreOffice 尽力渲染 PDF 预览
（降级如实记录），HTML 预览必出。保留父辈数字台账与双向比对。

## 安装

自包含 Skill；平台安装为 `/skills/weekly-skill` 后按 `SKILL.md` 执行。
本地复现仅需 Python 3.8+ 标准库（PDF 可选 `pdftotext`；docx→PDF 可选 LibreOffice）。

## 快速开始

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output; mkdir -p $W $O
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
python3 $S/number_engine.py ledger --work $W
# Agent 翻译 → translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/number_engine.py audit --work $W
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "editable-deliverables-plus v2.0.3"
python3 $S/assemble_result.py --work $W --out $O --skill "editable-deliverables-plus v2.0.3" --status success
python3 $S/make_docx.py --out $O --work $W        # 本版核心：docx + 尽力 PDF
python3 $S/render_previews.py --out $O --work $W  # HTML 预览必出
python3 $S/validate_output.py --out $O --work $W
```

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、稿件（md/txt/tex/docx/pdf）。
- 输出：md/docx/pdf/html 四形态译文与对照稿 + 机检产物 + `result.json`。

## 边界

- docx 为最小样式集；PDF 依赖环境 LibreOffice，缺失时 preview_status 如实降级。

## 仓库与维护

- GitHub：<https://github.com/Austin071031/Academic-Writing-Skill>（`学术翻译与双语写作/v2.0.3-可编辑交付物升级/`）
- 变更历史见 `CHANGELOG.md`（含 v1.0.1 评分基线）。
