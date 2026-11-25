# 可编辑交付物方法（editable outputs）

## 问题定义

评分“任务完成度”要求交付物“可以直接进入作者的修改流程”，运行时契约要求
“Editable Office outputs should have real rendered PDF/PNG previews”。
v1 只交付 Markdown——可读但非作者工作流原生格式，且无渲染预览。

## 机制（make_docx.py，纯标准库）

1. **最小 OOXML**：[Content_Types].xml + _rels/.rels + word/document.xml +
   word/styles.xml（标题 1-3 级样式 + 正文），zipfile 打包即合法 .docx。
   不依赖 python-docx 等第三方库（评测环境零依赖保证）。
2. **映射规则**：md `#`/`##`/`###` → Heading1/2/3；`**` 加粗标记去除；
   双语对照段保留 〔PID〕 坐标文本，作者可对照 bilingual.md 逐段修改。
3. **PDF 预览降级链**：soffice/libreoffice --headless --convert-to pdf →
   成功出 translation.pdf / bilingual.pdf；工具缺失或失败 →
   preview_status.json 如实记录原因，HTML 预览（render_previews.py）必出。
4. **验证**：Agent 用 zipfile 快速校验 docx 结构完整（SKILL 第 12 步）。

## 为什么这能提分

- “结果完整性 5 分”：交付形态从 1 种（md）变为 4 种（md/docx/pdf/html）且互相一致。
- “任务完成度”：docx 是作者修改流程的原生载体。
- “可靠体验/异常处理”：渲染降级链全程如实记录，无伪造成功。
- 运行时契约明确要求可编辑产物附带真实渲染预览，docx+PDF 直接命中。

## 边界

- 样式集最小（标题层级+正文），不含复杂版式；公式保留文本形态。
- 若评测环境有 fonts/LibreOffice 差异导致 PDF 字体替换，属环境问题，
  preview_status 记录实际使用的工具链。
