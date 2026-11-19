# 使用说明（mindmap-pipeline-engine v1.0.1）

## 输入

`/input/case.json`（case_id + output_contract）、`/input/task.md`、材料文件（md/txt/tex/html/docx/pdf）。

## 调用（`$S=/skills/weekly-skill/scripts`）

```bash
# Phase 0：落盘 + 勘察 + 解析
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_materials.py --work /app/work

# Phase 1：Agent 写 /app/work/mindmap.json（规范见 SKILL.md）

# Phase 2：一键管线
python3 $S/engine.py run --work /app/work --out /app/output --case /input/case.json \
    --status success --skill "mindmap-pipeline-engine v1.0.1"

# Phase 3：读 work/audit.json；有 critical 则修 mindmap.json 重跑 Phase 2
```

也可只跑结构修复：`python3 $S/engine.py fix --work /app/work`。

## engine.py 自动修复规则

| 触发 | 动作 | 留痕 |
|-|-|-|
| 节点扇出 >7 | 按 (kind, 证据材料号) 聚类插入 group 节点；单桶则按序切分（每组≤6） | change_log: auto_group |
| 深度 >6 | 超深子树上提一层 | change_log: lift_deep |
| 审计 critical 且 status=success | 自动降级 partial 并提示 | 标准输出 |

## 输出

`mindmap.md/.mm/.opml/.mmd/.svg/.html`（+.png 视环境）、`evidence_map.json`、
`audit_report.json`、`preview_status.json`、`result.json`。

## 自查

1. `work/audit.json` stats.n_critical=0；2. `validate_output.py` 退出码 0（engine 已内置调用）；
3. result.json 的 outputs 各项文件存在非空；4. change_log 中的自动分组符合语义（不符合时手工调整分组后重跑）。

## 失败处理

任一阶段失败追加 `work/exceptions.json`，以已有产物 `--status partial` 交付，
`work/uncertainty.json` 写明影响；禁止删除失败记录。
