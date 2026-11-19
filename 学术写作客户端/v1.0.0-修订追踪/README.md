# 学术写作客户端 · 修订追踪（v1）

## 这是什么

一个可被 Agent 调用的学术写作 Skill：给定学术稿件与修改指令，产出带 DOCX
原生修订的可编辑改稿、逐条改动台账、接受/拒绝两个变体和 PDF/PNG 预览，
并把结构化结果写入 `/app/output/result.json`。

## 依赖

- Python 3.8+（仅标准库，无 pip 安装）
- LibreOffice（`soffice`，仅预览渲染需要，可降级）
- `pdftoppm`（仅 PNG 预览需要，可降级）
- `pdftotext`（仅 PDF 稿件与目录页码回填需要，可降级）

## 目录结构

```
v1-修订追踪/
├── SKILL.md                 # Skill 本体（调用方式与执行流程）
├── README.md                # 本说明
├── scripts/
│   ├── docxkit.py           # OOXML/DOCX 工具包（修订、替换、审计、引用）
│   ├── workorder.py         # 指令→锚点定位，生成 edit_plan.json
│   ├── revisions_apply.py   # 应用修订：修订稿+台账+接受/拒绝变体
│   ├── audit_diff.py        # before/after 保真差分核验
│   ├── render_preview.py    # DOCX→PDF→PNG 预览渲染
│   └── result_builder.py    # 按 output_contract 构建诚实 result.json
├── references/
│   └── revision-tracking.md # 方法说明与核验清单
└── examples/
    └── minimal-example.md   # 最小调用示例（示意输出）
```

## 快速使用

```bash
SKILL_DIR=/skills/weekly-skill   # 以实际安装路径为准
cp /input/case.json /input/task.md /app/work/ 2>/dev/null
# 依次执行 SKILL.md“执行流程”的阶段 0–6
```

## 适用范围与限制

- 适用：DOCX 稿件的定点修改、术语统一、删句、增补、核对；章节化长稿。
- 限制：PDF 扫描件需 OCR 才能编辑；修订在 OOXML 文本层落地，对嵌入对象
  （OLE、SmartArt）内的文字不做修改；中文竖排、复杂域嵌套场景修订粒度为
  段落级。
- 维护：脚本为单文件纯标准库实现，可直接阅读修改；版本记录见
  `SKILL.md` frontmatter。

## 自查方法

按 `references/revision-tracking.md` 的核验清单逐条检查；
平台复核时以 `/app/output/result.json`、`change_log.json`、
修订稿与预览的实际内容为准。
