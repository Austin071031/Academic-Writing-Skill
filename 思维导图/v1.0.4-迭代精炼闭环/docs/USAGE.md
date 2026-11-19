# 使用说明（mindmap-refine-loop v1.0.4）

## 调用（`$S=/skills/weekly-skill/scripts`）

```bash
# Phase 0
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_materials.py --work /app/work

# Phase 1：快速草稿 work/mindmap.json（规范见 SKILL.md）

# Phase 2：第一轮机检
python3 $S/map_audit.py --work /app/work
python3 $S/refine.py --work /app/work

# Phase 3：按 work/fix_list.md 定向修订，然后复评
python3 $S/map_audit.py --work /app/work
python3 $S/refine.py --work /app/work
# 把两轮 overall 写入 work/stats.json: {"refine_rounds":[{"overall":72.1},{"overall":88.4}]}

# Phase 4：交付
python3 $S/map_render.py --work /app/work --out /app/output
cp /app/work/refine_report.json /app/output/refine_report.json
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "mindmap-refine-loop v1.0.4" --status success
python3 $S/validate_output.py --out /app/output --work /app/work
```

## refine_report.json 判读

- `scores`：五维得分；最低维即下一轮修订重点。
- `metrics.uncovered_important`：重要未覆盖单元数（>0 必有 high 级修复项）。
- `metrics.fact_quote_hit` / `number_traced`：抓得准的分子/分母。

## 修订优先级

1. critical（quote 非原文）→ 立即修，否则 fact 可信度归零；
2. high（重要单元未覆盖、证据节点率 <50%）→ 决定"完整性"与"可追溯"得分；
3. medium（扇出/重复标题/边过少）→ 决定"理得清/连得对"；
4. low（kind 混杂）→ 有余力再修。

## 输出

mindmap 六格式 + refine_report.json（质量自证）+ evidence_map.json + audit_report.json + result.json。

## 失败处理

两轮后仍有 high：如实 `--status partial`，`work/uncertainty.json` 列剩余项；
禁止删修复清单条目冒充完成。
