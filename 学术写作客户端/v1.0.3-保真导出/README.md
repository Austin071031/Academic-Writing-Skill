# 学术写作客户端 · 保真导出（v4）

## 这是什么

一个可被 Agent 调用的学术写作 Skill：完成定点修改后，把稿件经
“字体检查 → 真实渲染 → 目录页码回填 → 保真差分核验”的导出管线，
交付可编辑 DOCX、PDF/PNG 预览和保真报告，结果写入
`/app/output/result.json`。

## 依赖

- Python 3.8+（仅标准库）
- LibreOffice（soffice，渲染 PDF）
- poppler-utils（pdftoppm PNG 预览、pdftotext 页码定位）
- 以上缺失均可降级，但必须在报告中注明

## 目录结构

```
v4-保真导出/
├── SKILL.md
├── README.md
├── scripts/
│   ├── docxkit.py         # OOXML 工具包
│   ├── fidelity_export.py # 导出管线（font-check/render/toc-refresh/fidelity）
│   ├── audit_diff.py      # 差分引擎（被 fidelity_export 调用）
│   ├── render_preview.py  # 渲染引擎（被 fidelity_export 调用）
│   ├── workorder.py       # 指令锚定
│   └── result_builder.py  # 诚实 result.json
├── references/fidelity-export.md
└── examples/minimal-example.md
```

## 适用范围与限制

- 适用：需要 DOCX+PDF 双交付的修改任务；含目录、题注、公式的稿件。
- 限制：LibreOffice 与 Word 的排版引擎存在固有差异（行距、断行），
  保真核验覆盖内容与结构，不承诺像素级一致；嵌入 OLE 对象不展开核验。

## 自查方法

按 `references/fidelity-export.md` 核验清单执行；
以 `render_status.json`、`toc_report.json`、`fidelity.json` 实际内容为准。
