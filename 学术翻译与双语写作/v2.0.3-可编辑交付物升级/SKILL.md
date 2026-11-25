---
name: editable-deliverables-plus
description: 学术翻译技能（v2 迭代·主攻“结果完整性与可直接进入修改流程”：可编辑交付物升级）。在句段级翻译管线（父辈 v1.0.1 数字台账+双向比对）上增加 make_docx.py：纯标准库把纯译文与双语对照稿生成可编辑 Word 文档（translation.docx / bilingual.docx，标题层级映射、双语段保留 〔PID〕 坐标），并尽力用 LibreOffice 渲染真实 PDF 预览，工具缺失时在 preview_status.json 如实降级记录；HTML 预览必出。评分考察“可以直接进入作者的修改流程”，docx+PDF 预览使交付物开箱即用。当用户要求整篇翻译并交付可编辑稿件时使用；输入 /input 下稿件与 case.json，输出 /app/output 下 translation_full.md、bilingual.md、translation.docx、bilingual.docx、PDF/HTML 预览、number_audit.json、report.md、result.json。
---

# 可编辑交付物升级 · 学术翻译 Skill（v2.0.3，父辈 v1.0.1）

## 用途与适用条件

整篇学术稿件句段级翻译 + 数字忠实性机检（父辈机制）。**本版核心增量：交付物从纯 Markdown 升级为“可编辑 Word + 真实渲染 PDF 预览 + 必出 HTML 预览”**——直接满足评分“可编辑稿件、可直接进入作者修改流程”与运行时契约“editable outputs should have real rendered PDF/PNG previews”。

适用：整篇翻译并交付可编辑稿件的场景。不适用：纯数据无正文文件（如实降级）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、稿件；工作目录 `/app/work`；交付 `/app/output`。
- 预算：64 次模型请求 / 900 秒。译文追加写入 translations.jsonl，随时可组装。
- 本目录即技能根：`scripts/`、`references/`、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线

1. **渲染降级如实记录**：无 LibreOffice 时只交付 docx+HTML 预览，preview_status.json 写明原因，禁止声称已出 PDF。
2. **数字零臆造**（父辈）：译文每个数字能在源句段找到等值对应。
3. **不静默跳过句段**：未译句段以【缺译】标记并计 uncertainty。

## 标准工作流（严格按序执行）

```bash
SKILL_DIR=/skills/weekly-skill   # 平台安装路径；本地调试用本目录
W=/app/work; O=/app/output; mkdir -p $W $O
S=$SKILL_DIR/scripts

python3 $S/init_result.py
python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W
python3 $S/segment_builder.py --work $W
python3 $S/number_engine.py ledger --work $W
```

**第 6 步（Agent 翻译）**：打开 `work/source_for_translation.md` 分批翻译（每批 20–40 句段），追加写 `work/translations.jsonl`；数字对照台账，〔保留:…〕逐字符保留。预算兜底：请求用满 40 次仍未译完，进第 7 步按缺译交付 partial。

```bash
python3 $S/assemble_translation.py --work $W --out $O   # 7) 组装纯译文+双语对照
python3 $S/number_engine.py audit --work $W             # 8) 数字双向比对
```

**第 9 步（Agent 复核修订，禁止跳过）**：处置 number_audit issues，重跑 7、8 清零。

```bash
# 10) 报告 + 契约组装
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "editable-deliverables-plus v2.0.3"
python3 $S/assemble_result.py --work $W --out $O --skill "editable-deliverables-plus v2.0.3" --status success

# 11) 可编辑交付物 + 预览（本版核心步骤）
python3 $S/make_docx.py --out $O --work $W       # translation.docx + bilingual.docx（+尽力 PDF）
python3 $S/render_previews.py --out $O --work $W  # preview.html 必出
cat $O/preview_status.json    # 确认 docx/pdf/html 状态；降级原因须如实
python3 $S/validate_output.py --out $O --work $W
```

**第 12 步（Agent 交付确认）**：打开 preview_status.json 与 preview.html（或 PDF）抽查：
双语对照段 〔PID〕 坐标完整、标题层级正确、无缺译漏标；如 docx 打开异常（可用
python3 -c "import zipfile;zipfile.ZipFile('...')" 快速验证），修复后重跑第 11 步。

## 异常处理

| 情况 | 处置 |
|-|-|
| 无 LibreOffice | preview_status.json 记录“仅 docx+HTML 预览”；不算失败 |
| docx 生成失败 | 记录 exceptions；md 交付物仍完整，status≤partial |
| PDF 转换失败（soffice 报错） | 记录原因并跳过；HTML 预览仍必出 |
| 无稿件候选 / PDF 无文本层 | 骨架 failed / exceptions + status≤partial |
| 稿件无数字 | 零发现如实记录，不构成失败 |
| 超长稿件 / 脚本异常 | 分批 partial 兜底；脚本读 stderr 修复重跑（幂等） |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `translation_full.md` / `bilingual.md` | 纯译文 / 双语对照（Markdown 源） |
| `translation.docx` / `bilingual.docx` | 可编辑 Word 稿件（标题层级、双语 〔PID〕 坐标） |
| `translation.pdf` / `bilingual.pdf` | 真实渲染 PDF 预览（有 LibreOffice 时；否则 preview_status 记录降级） |
| `preview.html` / `preview_status.json` | HTML 预览（必出）/ 渲染状态记录 |
| `number_ledger.json` / `number_audit.json` | 数字台账与比对（父辈） |
| `result.json` | 契约结果：case_id、status、evidence_map、change_log、uncertainty |

## 关键方法（详见 references/）

- `references/editable_outputs.md`：最小 OOXML 结构、标题映射、降级链与验证方法。
- `references/number_rules.md`：数字归一与改动分级（父辈机制）。
- `references/failure_modes.md`：误报来源与复核要点。

## 限制

- docx 为最小样式集（标题 1-3 级 + 正文），复杂版式（页眉页脚/样式表）不在范围。
- PDF 预览依赖环境 LibreOffice；缺失时如实降级不补造。
- 公式在 docx 中以文本形态保留（不转 OMML），公式编辑请回 md/tex 源。
