# 最小调用示例（示意，非正式案例结果）

> 输入为合成文本；仅演示接口。

## 输入（合成会议纪要节选）

```
议题：LiF 中间层厚度。结论：采用 20 nm 方案（合作组建议）。
分歧：张认为 20 nm 足够，李认为需 30 nm 以覆盖晶界。
待办：李负责 30 nm 对比实验，截止下周五。
```

## 调用（关键片段）

```bash
python3 $S/parse_materials.py --work /app/work
# Agent 写 mindmap.json：
```

```json
{"root": "root", "title": "组会纪要：界面工程", "purpose": "决策追踪", "audience": "组员",
 "nodes": [
  {"id": "root", "title": "界面工程组会", "parent": null, "kind": "root", "evidence": [], "status": "confirmed"},
  {"id": "d1", "title": "决议: LiF 中间层 20 nm", "parent": "root", "kind": "decision",
   "status": "confirmed", "evidence": [{"unit": "M01-S01-P001", "type": "fact", "quote": "采用 20 nm 方案"}]},
  {"id": "v1", "title": "张: 20 nm 足够", "parent": "root", "kind": "debate",
   "status": "confirmed", "evidence": [{"unit": "M01-S01-P002", "type": "fact", "quote": "20 nm 足够"}]},
  {"id": "v2", "title": "李: 需 30 nm 覆盖晶界", "parent": "root", "kind": "debate",
   "status": "confirmed", "evidence": [{"unit": "M01-S01-P002", "type": "fact", "quote": "需 30 nm 以覆盖晶界"}]},
  {"id": "a1", "title": "待办: 李 30 nm 对比实验（下周五）", "parent": "root", "kind": "action",
   "status": "confirmed", "evidence": [{"unit": "M01-S01-P003", "type": "summary"}]}
 ],
 "edges": [
  {"from": "v1", "to": "v2", "relation": "conflicts", "evidence": [{"unit": "M01-S01-P002"}]},
  {"from": "a1", "to": "v2", "relation": "supports", "evidence": [{"unit": "M01-S01-P003"}]}
 ]}
```

```bash
python3 $S/relation_engine.py audit --work /app/work
# -> 边=2 问题=0 候选建议≈1（d1 与 v1 共享议题单元 → 建议 supports）
python3 $S/relation_engine.py render --work /app/work --out /app/output
# -> relations.mmd / relations.md / relations.svg
```

## 示意输出（relations.md）

```
| 起点 | 关系 | 终点 | 证据 |
| 张: 20 nm 足够 | conflicts | 李: 需 30 nm 覆盖晶界 | M01-S01-P002 |
| 待办: 李 30 nm 对比实验（下周五） | supports | 李: 需 30 nm 覆盖晶界 | M01-S01-P003 |
```
