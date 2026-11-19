# 学术写作客户端 · 引用协作（v2）

## 这是什么

一个可被 Agent 调用的学术写作 Skill：对含编号引用的学术稿件构建引用依赖图，
审计正文引用与参考文献表的一致性（乱序、缺号、未引用、DOI），并按指令做
确定性重编号同步，交付可编辑 DOCX、逐条改写报告与 PDF/PNG 预览，
结果写入 `/app/output/result.json`。

## 依赖

- Python 3.8+（仅标准库）
- LibreOffice / pdftoppm（预览渲染，可降级）

## 目录结构

```
v2-引用协作/
├── SKILL.md
├── README.md
├── scripts/
│   ├── docxkit.py        # OOXML 工具包（跨 run 替换、引用提取）
│   ├── citation_sync.py  # 依赖图、审计、重编号同步
│   ├── audit_diff.py     # 保真差分核验
│   ├── render_preview.py # DOCX→PDF→PNG 预览
│   ├── workorder.py      # 其他修改指令的锚定（如案例含非引用指令）
│   └── result_builder.py # 诚实 result.json
├── references/citation-collaboration.md
└── examples/minimal-example.md
```

## 适用范围与限制

- 适用：编号制引用（[n]、[n,m]、[n-m]）的中英文稿件；GB/T 7714、Vancouver。
- 限制：作者-年份制稿件不做编号同步（只做条目/DOI 核对）；域代码内的
  引文只改显示文本；不联网核验 DOI 真实性（形态校验 only）。

## 自查方法

按 `references/citation-collaboration.md` 核验清单执行；
以 `citation_audit.json`、`sync_report.json`、`post_audit.json` 三份报告的
实际内容为准。
