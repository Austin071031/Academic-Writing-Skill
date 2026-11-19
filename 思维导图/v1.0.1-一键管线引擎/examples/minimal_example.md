# 最小调用示例（示意，非正式案例结果）

> 输入为合成文本；仅演示接口。

## 输入

`/input/task.md`：为材料制作思维导图，受众为评审专家，用途为项目进展汇报。
`/input/plan.md`（合成）：含目标、两个里程碑、三项任务与两条风险。

## 调用

```bash
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --input-dir /input --work /app/work
python3 $S/parse_materials.py --work /app/work
# Agent 写 work/mindmap.json（含 12 个子节点挂同一父节点，故意超扇出）
python3 $S/engine.py run --work /app/work --out /app/output --case /input/case.json \
    --status success --skill "mindmap-pipeline-engine v1.0.1"
```

## 示意输出（引擎日志）

```
[engine] fix: 自动修复 1 处            # 12 个子节点自动分为 里程碑/任务/风险 三组
  [map_audit.py] 节点=15 边=2 覆盖率=0.71 critical=0 warning=0 规范化修复=0
  [map_render.py] mindmap: 已渲染 ['md','mm','opml','mmd','html','svg','png']
  [assemble_result.py] status=success outputs=9 项 -> result.json
  [validate_output.py] [validate] PASS (status=success)
```

change_log.json 含 `{"op":"auto_group","location":"n02","before":12,"after":3,...}`，可复核。
