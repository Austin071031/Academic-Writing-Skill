# OOXML/OPC 实战坑位与环境备忘

本文件记录本 Skill 已内置处理的 OOXML/OPC 层坑位（全部实测验证），供维护与复用时参考。对应实现见 `scripts/ooxml.py`、`scripts/adapt_docx.py`、`scripts/render_preview.py`。

1. **子元素顺序是硬约束**。w:pPr 必须最先；w:rPr、w:style、w:lvl、w:sectPr 都有 schema 顺序。顺序错时 LibreOffice 直接报"source file could not be loaded"且不指位置。实现：canonical order 表 + 顺序插入 + 保存前整体排序（`sort_children_in_place`）。
2. **OPC 关系与默认命名空间**。`word/_rels/document.xml.rels` 中 styles/numbering/footer 等部件必须建立关系且 Target 相对 `word/`（写 `footer1.xml` 不是 `word/footer1.xml`）；`.rels` 与 `[Content_Types].xml` 根元素必须用默认命名空间（禁止前缀），否则 LO 的 OPC 读取器失败。实现：字符串级 flat 解析/序列化（quote-aware），新增部件时自动注册关系与内容类型。
3. **样式绑定而非外观模仿**。标题层级走 styles.xml + numbering.xml 抽象编号；正文 run 级字体/字号归一化但跳过超链接、域、修订（w:ins/w:del）内部。
4. **内嵌编号防重复**。稿件文本已带"第X章 / 1.1"的标题段落，在样式编号下会显示双重编号；适配时对该段落加 numPr numId=0 抑制样式编号，文字编号原样保留（不动文本）。
5. **三线表精确规格**。顶/底 1.5pt（sz=12 八分之一磅单位）、表头下 0.75pt（sz=6）、其余框线 nil、表格 jc=center、首行 tblHeader 跨页重复。
6. **目录要真页码**。TOC 域以 begin/instrText/separate/缓存条目/end 完整结构插入（Word 可 F9 刷新）；两遍渲染：第一遍导出 PDF → pdftotext 逐页定位标题页码（空白剥离匹配，优先非目录页命中）→ 回填缓存条目页码 → 第二遍导出。目录条目段落用 TOC1-3 样式标记，保真度比对按结构豁免。
7. **保真要差分报告**。段落文本序列（有序包含）、表格单元格、图片字节级、公式/超链接/书签/脚注/批注/修订/域计数逐项比对；新增白名单只含目录生成内容。
8. **扫描件判定**。pdftotext 抽取 < 400 字符判扫描件，如实标 failed 并说明需 OCR，绝不把空内容当成功。
9. **字体与导出核验**。Times New Roman 缺失时 docx 保留指定字体名、渲染由 Liberation Serif 度量兼容替换（本赛题 revision3 官方配置）；用 pdfinfo 实测页面尺寸、pdffonts 核验嵌入，不信文档内部设置。
10. **单位换算表**。twips = 1/20 磅；mm = twips × 25.4/1440；中文字号（小四=12pt、五号=10.5pt）；1.5 倍行距 = w:spacing line=360 lineRule=auto；页边距中文要求一般是 cm（抽取时 ×10 转 mm）。
11. **ElementTree 全局命名空间注册只有一份**。同一进程内不能给两个不同 URI 注册默认命名空间，否则 .rels 序列化退化为 ns0: 前缀。实现：OPC 两个扁平部件不走 ET，用字符串级处理。
12. **zipfile 重写不增不删**。保存时按原部件集合全量回写（确定性排序），不新建包骨架，保留 customXml、theme、thumbnail 等未动部件原样。

## 环境备忘（赛题运行环境）

- Python 3.12、LibreOffice、pandoc、poppler-utils 均已预装；Liberation Serif 等 Liberation 系列字体可用。
- 本 Skill 纯标准库，不 pip install 任何包；若你手工扩展，优先保持零依赖。
- /input 可能只读：一切写入只在 /app/work 与 /app/output。
