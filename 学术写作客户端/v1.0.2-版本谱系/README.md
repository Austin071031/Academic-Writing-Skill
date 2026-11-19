# 学术写作客户端 · 版本谱系（v3）

## 这是什么

一个可被 Agent 调用的学术写作 Skill：对稿件的每个状态做内容寻址不可变
快照，维护谱系 manifest，支持版本间段落级 diff 与可校验回退，
交付最终稿、谱系 manifest、diff 报告与 PDF/PNG 预览，
结果写入 `/app/output/result.json`。

## 依赖

- Python 3.8+（仅标准库）
- LibreOffice / pdftoppm（预览渲染，可降级）

## 目录结构

```
v3-版本谱系/
├── SKILL.md
├── README.md
├── scripts/
│   ├── docxkit.py        # OOXML 工具包（定点修改与提取）
│   ├── lineage.py        # 快照 / manifest / diff / restore / verify
│   ├── workorder.py      # 指令锚定
│   ├── audit_diff.py     # 保真差分核验
│   ├── render_preview.py # 预览渲染
│   └── result_builder.py # 诚实 result.json
├── references/version-lineage.md
└── examples/minimal-example.md
```

## 适用范围与限制

- 适用：多轮修改、版本对比、回退要求的写作任务；单篇或多篇 DOCX 稿件。
- 限制：二进制大文件（>100MB）快照开销大；vault 与被管稿件需同卷；
  diff 为段落级文本对比，不比较排版像素。

## 自查方法

按 `references/version-lineage.md` 核验清单执行；
以 `lineage.json`、`version_diff.json` 的实际内容为准。
