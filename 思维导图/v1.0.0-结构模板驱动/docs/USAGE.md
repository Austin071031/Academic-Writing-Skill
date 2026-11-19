# 使用说明（mindmap-template-studio v1.0.0）

## 输入

- `/input/case.json`：案例描述，含 `case_id` 与 `output_contract`（交付字段契约）。
- `/input/task.md`：任务说明（用途、受众、格式要求）。
- `/input/` 下其余文件：科研材料（md/txt/tex/html/docx/pdf；多份混合均可）。

## 调用步骤（逐字命令，`$S=/skills/weekly-skill/scripts`）

```bash
# 0. 落盘骨架 + 勘察
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
# 1. 材料解析（单元号 = 溯源锚点）
python3 $S/parse_materials.py --work /app/work
# 2. 材料类型识别 + 骨架模板
python3 $S/templates.py --work /app/work
# 3. Agent 按 slot_checklist.md 把 skeleton.json 填成 work/mindmap.json
# 4. 审计（critical 修完重跑一次）
python3 $S/map_audit.py --work /app/work
# 5. 渲染 + 汇总 + 闸门
python3 $S/map_render.py --work /app/work --out /app/output
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "mindmap-template-studio v1.0.0" --status success
python3 $S/validate_output.py --out /app/output --work /app/work
```

## 输出（/app/output）

| 文件 | 说明 |
|-|-|
| mindmap.md | Markdown 大纲（节点附证据锚点，可直接编辑） |
| mindmap.mm | FreeMind XML，XMind/Freeplane 可导入；证据锚点存于 LINK 属性 |
| mindmap.opml | OPML 大纲，主流导图工具可导入 |
| mindmap.mmd | Mermaid mindmap 源码 |
| mindmap.svg / .png / .html | 渲染预览（HTML 可折叠浏览） |
| evidence_map.json | 节点 → 材料单元/页码/类型的溯源映射 |
| audit_report.json | 审计问题与统计（覆盖率、critical/warning 数） |
| result.json | 汇总：case_id、status、outputs、uncertainty、exceptions、stats |

## 中间文件（/app/work）

`inspection.json`、`materials.json`（全部单元原文）、`materials_digest.md`（压缩目录）、
`skeleton.json`、`slot_checklist.md`、`mindmap.json`（Agent 手写）、
`mindmap.normalized.json`、`audit.json`、`change_log.json`、`uncertainty.json`。

## 自查方法

1. `audit.json` 的 `stats.n_critical` 必须为 0 才能 `--status success`。
2. 抽查 3 个 fact 证据：quote 能否在 materials.json 对应单元原文中找到（应逐字命中）。
3. `validate_output.py` 退出码 0。
4. result.json 含 case_id 且 output_contract 声明的字段均非 null。

## 失败处理

任一阶段失败：把现象与原因追加到 `work/exceptions.json`（JSON 数组），用其余材料继续，
最终 `--status partial` 并在 `work/uncertainty.json` 说明影响范围与人工建议。
禁止删除失败记录冒充成功。
