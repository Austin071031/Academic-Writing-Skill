# 学术写作客户端 · 锚定式 AI 修改（v5）

## 这是什么

一个可被 Agent 调用的学术写作 Skill：把自然语言修改指令分解为锚定到
原稿具体句子的原子改动，机械执行最小改写，并由漂移守卫脚本核验
“改得准、改得小、没改别处、数字没漂”，交付带修订记录的改稿、
漂移报告与 PDF/PNG 预览，结果写入 `/app/output/result.json`。

## 依赖

- Python 3.8+（仅标准库）
- LibreOffice / pdftoppm（预览渲染，可降级）

## 目录结构

```
v5-锚定式AI修改/
├── SKILL.md
├── README.md
├── scripts/
│   ├── docxkit.py        # OOXML 工具包（跨 run 最小替换、修订）
│   ├── drift_guard.py    # 语义漂移守卫（锚定/幅度/净土/数字守恒）
│   ├── workorder.py      # 指令机器锚定
│   ├── revisions_apply.py# 原子改动落地 + 台账
│   ├── audit_diff.py     # 保真差分核验
│   ├── render_preview.py # 预览渲染
│   └── result_builder.py # 诚实 result.json
├── references/anchored-editing.md
└── examples/minimal-example.md
```

## 适用范围与限制

- 适用：措辞润色、术语统一、删句、段后增补、事实核对等指令型修改。
- 限制：需要重排章节结构或大幅重写论证链的指令不在“最小改动”射程内，
  应显式标 human_confirmations；守卫阈值为工程近似，临界情况以人工复核为准。

## 自查方法

按 `references/anchored-editing.md` 核验清单执行；
以 `drift_report.json`、`changes.json` 实际内容为准。
