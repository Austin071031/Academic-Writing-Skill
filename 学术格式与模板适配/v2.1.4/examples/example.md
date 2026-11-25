# 最小调用示例（示意）

> **声明**：本示例为合成演示，输入为作者构造的最小稿件/模板，输出为**示意**（不冒充正式案例结果）。正式案例由平台在运行时注入 `/input/case.json` 与材料。

## 输入

`/input/case.json`（示意）：

```json
{
  "case_id": "demo-case-001",
  "task": "将 manuscript.docx 按 template.docx 模板适配：A4，页边距上2.5cm下2.5cm左3.0cm右2.0cm，正文小四宋体/Times New Roman、1.5倍行距，三线表，题注五号居中，参考文献GB/T 7714悬挂缩进，页脚居中页码，生成目录。",
  "materials": [
    {"path": "manuscript.docx", "role": "manuscript"},
    {"path": "template.docx", "role": "template"}
  ],
  "output_contract": {"adapted_docx": "改编后的可编辑docx", "compliance_report": "合规检查报告"}
}
```

## 调用

```bash
python3 /skills/weekly-skill/scripts/run_pipeline.py \
    --case /input/case.json --task /input/task.md \
    --work /app/work --outdir /app/output
```

## 示意输出（节选）

控制台（示意）：

```
[stage:inspect] success
[stage:measure] success
[stage:spec] success
[stage:convert_source] success
[stage:adapt] success
[stage:fidelity] success
[stage:compliance] success
[stage:render] success
[stage:result] success
```

`/app/output/result.json`（示意，截断）：

```json
{
  "case_id": "demo-case-001",
  "status": "success",
  "deliverables": [
    {"path": "/app/output/manuscript_adapted.docx", "type": "editable_docx", "description": "按目标模板结构化套用后的可编辑稿件"},
    {"path": "/app/output/manuscript_adapted.pdf", "type": "rendered_pdf", "description": "真实渲染 PDF"},
    {"path": "/app/output/preview-1.png", "type": "preview_png", "description": "渲染预览图"}
  ],
  "output_contract_filled": {
    "adapted_docx": "/app/output/manuscript_adapted.docx",
    "compliance_report": "/app/work/compliance.md"
  },
  "verification": {
    "compliance": {"PASS": 21, "FAIL": 0, "WARN": 0, "SKIP": 0},
    "fidelity_verdict": "PASS",
    "render": {"status": "success", "page_size": {"width_mm": 210.01, "height_mm": 297.0}, "all_fonts_embedded": true}
  },
  "uncertainty": {"unresolved_spec_items": [], "conflicts": [], "assumptions": []},
  "limits": ["未发现已知限制；未确认项见 uncertainty.unresolved_spec_items"]
}
```

## 预期行为要点

1. `checklist.md` 中的页边距/字号等数值来自模板文件实测（非猜测）；任务文本与模板冲突时文本优先并在 `spec.json.conflicts` 登记。
2. `fidelity.md` 显示原文全部段落/单元格按序保留、图片字节一致；目录条目为白名单新增。
3. `compliance.md` 逐项列出实测值与期望值（PASS/FAIL/SKIP）。
4. 目录页码为两遍渲染回填的真实页码，Word 打开后仍可 F9 刷新。
