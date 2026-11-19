# 最小调用示例（示意，非正式案例结果）

> 本示例仅说明接口与流程；输入为合成文本，输出为示意产物，不代表任何正式评测案例。

## 输入

`/input/task.md`：

```
任务：为材料制作思维导图。受众: 课题组新成员。用途: 论文结构梳理。
```

`/input/paper.md`（合成）：一篇关于固态电解质的短文，含 摘要/引言/方法/结果/结论 五节。

## 调用

```bash
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --input-dir /input --work /app/work
python3 $S/parse_materials.py --work /app/work
python3 $S/templates.py --work /app/work
# -> [templates] 材料类型=paper 槽位=6
# Agent 按 slot_checklist.md 填写 work/mindmap.json（节选）:
```

```json
{"title": "硫化物固态电解质界面稳定性研究", "root": "root",
 "nodes": [
  {"id": "root", "title": "Li3PS4 界面稳定性研究", "parent": null, "kind": "root", "evidence": [], "status": "confirmed"},
  {"id": "n01", "title": "研究问题: 界面副反应导致容量衰减", "parent": "root", "kind": "question",
   "status": "confirmed",
   "evidence": [{"unit": "M02-S03-P001", "type": "fact", "quote": "界面副反应导致容量衰减"}]},
  {"id": "n02", "title": "结果: 阻抗 45→320 Ω，增幅 611%", "parent": "root", "kind": "evidence",
   "status": "confirmed",
   "evidence": [{"unit": "M02-S07-P001", "type": "fact", "quote": "界面阻抗从 45 Ω 上升至 320 Ω，增幅 611%"}]}
 ],
 "edges": [{"from": "n01", "to": "n02", "relation": "causes",
            "evidence": [{"unit": "M02-S07-P001"}]}]}
```

```bash
python3 $S/map_audit.py --work /app/work
# -> [map_audit] 节点=3 边=1 覆盖率=0.13 critical=0 warning=0
python3 $S/map_render.py --work /app/work --out /app/output
python3 $S/assemble_result.py --work /app/work --out /app/output --skill "mindmap-template-studio v1.0.0" --status success
python3 $S/validate_output.py --out /app/output --work /app/work
# -> [validate] PASS
```

## 示意输出

`mindmap.md`（节选）：

```
# 硫化物固态电解质界面稳定性研究
- **Li3PS4 界面稳定性研究**
  - **研究问题: 界面副反应导致容量衰减** [M02-S03-P001]
  - **结果: 阻抗 45→320 Ω，增幅 611%** [M02-S07-P001]
## 关系
- 研究问题: 界面副反应导致容量衰减 —*causes*→ 结果: 阻抗 45→320 Ω，增幅 611% [M02-S07-P001]
```

正式交付还包含 mindmap.mm/.opml/.mmd/.svg/.html、evidence_map.json、audit_report.json 与 result.json。
