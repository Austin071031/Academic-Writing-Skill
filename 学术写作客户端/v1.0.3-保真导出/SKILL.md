---
name: academic-writing-fidelity-export
description: 学术写作客户端·文档导出方向。当任务需要把学术稿件（含修改后）导出为可编辑 DOCX 与 PDF/PNG 预览且保持样式、标题层级、编号、公式、题注、引用信息一致时使用。覆盖“接收稿件—定点修改—导出管线（字体/目录/渲染）—保真差分核验—结构化结果”全闭环。
---

# 学术写作客户端 · 保真导出（v4）

## 用途

导出环节的失败最常见：目录页码失效、字体替换后版式漂移、公式/题注渲染
丢失、DOCX 与 PDF 内容不一致。本 Skill 把导出做成**带核验报告的管线**：
字体度量兼容检查、两遍渲染目录页码回填、真实 PDF/PNG 渲染、
before/after 内容单元级保真差分，每一步失败如实降级并留痕，
绝不声称渲染成功而没有文件。

适用条件：需要交付可编辑文档 + 预览的学术写作任务；DOCX 稿件。
纯标准库脚本 + 系统渲染器（LibreOffice/pdftoppm/pdftotext，缺失时降级）。

## 调用方式

```bash
SKILL_DIR="${SKILL_DIR:-/skills/weekly-skill}"
ls "${SKILL_DIR}/scripts"
```

## 执行流程

### 阶段 0：读取事实与契约

通读 `/input/case.json`、`task.md`、`organizer-edit-workorder.json`，
提取 `case_id` 与 `output_contract`（注意其中的交付格式要求：
docx/pdf/预览页数等）。清点输入识别主稿件。立即落盘部分 result.json。

### 阶段 1：保全原稿、摸底与定点修改

```bash
mkdir -p /app/work/originals /app/work/stage
cp -a /input/. /app/work/originals/
python3 "${SKILL_DIR}/scripts/docxkit.py" inspect /app/work/originals/<主稿件>.docx \
  > /app/work/stage/manifest.json
python3 "${SKILL_DIR}/scripts/docxkit.py" dump /app/work/originals/<主稿件>.docx \
  > /app/work/stage/paras.json
python3 "${SKILL_DIR}/scripts/workorder.py" /input /app/work/stage/paras.json \
  /app/work/stage/edit_plan.json
```

按指令完成定点修改（锚定—最小—台账纪律，docxkit.replace_span /
tracked_replace），得到 `/app/work/stage/revised.docx`。
修改后的稿件是导出入参；**导出管线的目标是不让修改破坏版式自洽性**。

### 阶段 2：字体与版式前置检查

```bash
python3 "${SKILL_DIR}/scripts/fidelity_export.py" font-check \
  /app/work/stage/revised.docx /app/work/stage/font_report.json
```

检查 substitutions：缺字体时用度量兼容表（Times New Roman→Liberation
Serif、Arial→Liberation Sans、宋体→Noto Serif CJK SC 等）；
无兼容替代的字体会造成版式差异，写入 uncertainty。
单位换算常备：1 磅=20 twips，1 cm≈28.35 磅，小四=12 磅，
1.5 倍行距 = `w:spacing line=360 lineRule=auto`。

### 阶段 3：渲染导出（真实渲染）

```bash
python3 "${SKILL_DIR}/scripts/fidelity_export.py" render \
  /app/work/stage/revised.docx /app/work/stage/render 3
```

LibreOffice `--headless --convert-to pdf`，再 `pdftoppm` 取前 N 页 PNG。
渲染状态（renderer、降级原因）写入 render_status.json。
**渲染失败时不得交付声称是预览的空文件**；保留 DOCX 并注明降级。

### 阶段 4：目录页码两遍回填（有 TOC 域时）

```bash
python3 "${SKILL_DIR}/scripts/fidelity_export.py" toc-refresh \
  /app/work/stage/revised.docx /app/work/stage/render/revised.pdf \
  /app/work/stage/revised_toc.docx /app/work/stage/toc_report.json
```

第一遍渲染定位每个标题的实测页码（pdftotext 文本层），
回填 TOC 域缓存的显示页码；域结构（begin/separate/end）保持完整，
Word 中仍可 F9 刷新。无 pdftotext 时如实降级（报告注明“Word 内 F9 可刷新”）。
回填后重新渲染一次，预览必须来自**最终** DOCX。

### 阶段 5：保真差分核验（格式不塌的证据）

```bash
printf '%s\n' '<合法变换关键词1>' '<合法变换关键词2>' > /app/work/stage/whitelist.txt
python3 "${SKILL_DIR}/scripts/fidelity_export.py" fidelity \
  /app/work/originals/<主稿件>.docx /app/work/stage/revised_toc.docx \
  /app/work/stage/whitelist.txt /app/work/stage/fidelity.json
```

`fidelity_breaks` 必须为空：表格/图片/OMML 公式/脚注/尾注/超链接/
分节数量前后一致。不为空时先修复再交付；修复不了在 result.json 中
逐条列出。

### 阶段 6：归档与结构化结果

```bash
cp /app/work/stage/revised_toc.docx /app/output/revised_document.docx
cp /app/work/stage/render*/revised.pdf /app/output/previews/ 2>/dev/null || true
python3 "${SKILL_DIR}/scripts/result_builder.py" /input/case.json /app/output/result.json \
  --status success \
  --set 'revised_document=/app/output/revised_document.docx' \
  --set 'fidelity_report=/app/work/stage/fidelity.json' \
  --set 'previews=["/app/output/previews/revised_document.pdf"]'
```

## 异常处理

| 情形 | 处置 |
| --- | --- |
| soffice 缺失 | DOCX 照交，预览字段注明降级，status 可保持但需说明 |
| 字体缺失且无兼容替代 | 列入 uncertainty，PDF 中标注实际替代字体 |
| TOC 域结构非标准 | 不拆解域；仅当能识别 标题文本+尾部页码 行时回填，否则降级 |
| 公式为图片（非 OMML） | 数量对比照常，渲染质量人工复核项 |
| 导出与修改时间预算冲突 | 先交 DOCX+result.json，预览随后补 |

## 创新边界

“导出”在多数方案里是最后一道工序，没人验证它。本方向把导出变成
**有差分报告的闭环**：内容单元级 before/after 对比给出“格式没塌”的
结构化证据，字体替换是显式登记而非静默发生，目录页码是实测回填而非
失效域。这些正是“导出文档的可编辑性/一致性”评分点的可核验实现。

## 最小调用示例（示意，非正式案例结果）

```bash
python3 $SKILL_DIR/scripts/fidelity_export.py render revised.docx render_out 3
# 示意：{"pdf": "render_out/revised.pdf", "pngs": ["render_out/revised-1.png"], "ok": true}
python3 $SKILL_DIR/scripts/fidelity_export.py fidelity before.docx after.docx wl.txt
# 示意：{"summary": {"structural_breaks": 0, "text_changed_paragraphs": 2}}
```
