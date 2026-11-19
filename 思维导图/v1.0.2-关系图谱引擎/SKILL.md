---
name: concept-relation-mapper
description: 关系图谱式思维导图生成，主打"连得对"。当用户要求从科研材料（论文/综述/实验记录/会议纪要）梳理概念关系、因果链、证据支持网络、观点冲突或研究脉络并生成思维导图/关系图时触发；只要层级大纲不要关系标注、或与科研材料无关时优先选用其他方式。除常规导图六格式外，额外交付类型化关系图（relations.mmd/svg/md）：七类关系逐条挂证据、方向冲突机检、数字冲突候选与缺失关系建议，全部产物落 /app/output。
---

# 思维导图 Skill（关系图谱引擎 · concept-relation-mapper）

核心思想：**思维导图的价值一半在"关系"**。基础 Agent 往往只给层级树、连边无依据；本 Skill 强制"每条边一种关系类型 + 一份证据"，并用引擎检出方向冲突、数字矛盾与缺失关系。

## 何时使用 / 不使用

- 使用：材料中存在明显因果、依赖、对比、时间、引用、支持、冲突关系（论文论证链、实验变量链、方案步骤、会议分歧）。
- 不使用：材料是纯罗列且无关系信息；只要简单大纲。

## 运行时契约

- 输入 `/input/case.json`、`/input/task.md`、材料文件；工作目录 `/app/work`；产物 `/app/output`（`result.json` 含 output_contract 全部字段与 case_id）。
- 预算 64 请求 / 900 秒 / 16384 token；脚本目录记作 `$S` = `/skills/weekly-skill/scripts/`（以实际安装目录为准）。
- 仅用 Python3 标准库；无网络假设。

## 三条红线

1. 不得编造事实、数字与"材料里没有依据的连接"；无证据的推断边必须在 note 写明"推断"并把端点标 uncertain。
2. `type="fact"` 的 `quote` 必须是原文子串；数字必须见于证据单元。
3. 审计 critical（含方向冲突、词表外关系）必须修复或如实降级 partial，不得隐瞒。

## 关系类型体系（七类，必须只用这七类）

| relation | 含义 | 方向 | 典型场景 |
|-|-|-|-|
| causes | 导致 | 有向 | 界面副反应 → 阻抗上升 |
| depends_on | 依赖 | 有向 | 任务B → 任务A；结论 → 前提假设 |
| precedes | 先于 | 有向 | 步骤/里程碑时间序 |
| contrasts | 对比 | 无向 | 两种方法/结果对比 |
| conflicts | 冲突 | 无向 | 互相矛盾的结论或数字 |
| supports | 支持 | 有向 | 证据 → 结论 |
| cites | 引用/出自 | 有向 | 节点 → 来源概念/文献线索 |

## 总流程

### Phase 0 落盘、勘察与解析

```bash
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_materials.py --work /app/work
```

读 `work/materials_digest.md` 掌握全局；需要原文按单元号到 `work/materials.json` 取。

### Phase 1 构建"节点 + 类型化边"的 mindmap.json

写入 `/app/work/mindmap.json`，规范：

```json
{
  "title": "导图标题", "purpose": "用途", "audience": "受众", "root": "root",
  "nodes": [
    {"id": "root", "title": "主题", "parent": null, "kind": "root", "note": "",
     "status": "confirmed", "evidence": []},
    {"id": "n01", "title": "节点标题（≤30字）", "parent": "root", "kind": "evidence",
     "note": "", "status": "confirmed",
     "evidence": [{"unit": "M02-S03-P001", "type": "fact", "quote": "原文逐字片段"}]}
  ],
  "edges": [
    {"from": "n01", "to": "n02", "relation": "supports",
     "evidence": [{"unit": "M02-S03-P001"}], "note": ""}
  ]
}
```

- `kind`：root/question/background/method/evidence/conclusion/limitation/task/risk/concept/decision/action/milestone/variable/control/criteria/step/goal/dependency/deliverable/topic/group。
- 层级树表达"包含/分类"，**edges 表达跨分支语义关系**；两者互补，不要用层级代替关系。
- 每个事实节点与每条边都要挂 evidence；推断边 note 写"推断"并标 uncertain。
- 覆盖目标：边数 ≥ 节点数的 1/8；结论类节点至少有一条 supports 入边。

### Phase 2 双层审计

```bash
python3 $S/map_audit.py --work /app/work
python3 $S/relation_engine.py audit --work /app/work
```

- `audit.json`：节点/证据层（quote 逐字、数字溯源、覆盖率）。
- `relation_audit.json`：关系层——边证据缺失、双向有向冲突、**数字冲突候选**（同主体不同数字）、
  **缺失关系建议**（共享证据单元但无边的节点对）。
按两份报告修订 mindmap.json 后重跑本阶段，直至 critical=0。

### Phase 3 渲染与交付

```bash
python3 $S/map_render.py --work /app/work --out /app/output
python3 $S/relation_engine.py render --work /app/work --out /app/output
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "concept-relation-mapper v1.0.2" --status success
python3 $S/validate_output.py --out /app/output --work /app/work
```

交付物：层级导图六格式（mindmap.md/.mm/.opml/.mmd/.svg/.html，+.png 若环境支持）
+ 关系图三件套（relations.mmd/.svg/.md）+ evidence_map.json + audit_report.json + result.json。
有未修复 critical 或材料缺口时 `--status partial` 并写 `work/uncertainty.json`（JSON 数组）。

## 异常处置表

| 异常 | 处置 |
|-|-|
| 材料解析失败 | exceptions 已记录，用其余材料继续，uncertainty 标注 |
| 材料间数字冲突 | 两节点并列 + conflicts 边，双方挂证据，标 uncertain；勿擅自二选一 |
| 方向冲突告警 | 核实逻辑后保留正确方向一条 |
| 关系词表外需求 | 归入最近一类并在 note 说明，禁止自造 relation 值 |
| 边证据难找 | 该边多半不成立：删除或标"推断"+uncertain |
| 预算过半 | 立即以当前版本跑 Phase 2-3，status=partial |

## 预算兜底

第 1 个响应完成 Phase 0；40 次请求前必须已进入 Phase 3；中断时 result.json 至少是骨架。
