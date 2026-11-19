---
name: mindmap-atlas
description: 分层图集式思维导图生成，专治大材料节点爆炸。当用户要求从较长或较多的科研材料（论文全文/多篇文献/项目文档/会议记录合集）生成思维导图，或明确要求"总览+细节"分层组织时触发；材料很短（一两页）且只要单张大图时也可使用但会以单图模式交付。交付"1 张总览图 + N 张分主题详图"的图集：每图六格式可编辑源（md/mm/opml/mmd/svg/html）+ 跨图稳定编号 + atlas_index.md/atlas.html 导航 + 逐节点证据溯源 + result.json。
---

# 思维导图 Skill（分层图集 · mindmap-atlas）

核心思想：**大图不等于好图**。超过 40 节点的单图无法阅读；本 Skill 先把材料组织成一棵完整逻辑树，再由图集引擎按预算自动拆成"总览图 + 分主题详图"，编号全局稳定、可跨图溯源。

## 何时使用 / 不使用

- 使用：材料较长（论文全文、多份文档）、主题分支多、需要既看全局又查细节。
- 不使用：材料极短且分支很少（仍可用，引擎自动单图模式）。

## 运行时契约

- 输入 `/input/case.json`、`/input/task.md`、材料文件；工作目录 `/app/work`；产物 `/app/output`（`result.json` 含 output_contract 全部字段与 case_id）。
- 预算 64 请求 / 900 秒 / 16384 token；脚本目录记作 `$S` = `/skills/weekly-skill/scripts/`（以实际安装目录为准）。
- 仅用 Python3 标准库；无网络假设。

## 三条红线

1. 不得编造事实、数字、单元号；材料没有的内容标 `status="missing"`。
2. `type="fact"` 的 `quote` 必须是原文子串；数字必须见于证据单元。
3. 审计 critical 必须修复或如实 partial；图集拆分由引擎完成，禁止手工删节点凑预算。

## 总流程

### Phase 0 落盘、勘察与解析

```bash
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_materials.py --work /app/work
```

读 `work/materials_digest.md` 掌握全局；需要原文按单元号到 `work/materials.json` 取。

### Phase 1 设计"一级分支"（图集质量的决定性步骤）

一级分支即未来的"分主题详图"。按材料类型选 4–7 个互斥且穷尽的分支维度：

- 论文：研究问题 / 方法 / 结果与证据 / 结论与局限（背景并入问题）
- 综述：范围与框架 / 流派A..N / 共识 / 分歧 / 空白
- 实验方案：目标与假设 / 变量 / 步骤 / 对照与判定 / 风险
- 项目计划：目标 / 里程碑 / 任务与依赖 / 交付物 / 风险
- 会议纪要：议题与结论 / 分歧 / 待办 / 风险

分支下再自由展开 2–4 层。总量预期 >40 节点时**不要**刻意压缩——引擎会拆分。

### Phase 2 写 mindmap.json

规范（字段缺一不可）：

```json
{
  "title": "导图标题", "purpose": "用途", "audience": "受众", "root": "root",
  "nodes": [
    {"id": "root", "title": "主题", "parent": null, "kind": "root", "note": "",
     "status": "confirmed", "evidence": []},
    {"id": "n01", "title": "节点标题（≤30字）", "parent": "root", "kind": "method",
     "note": "", "status": "confirmed",
     "evidence": [{"unit": "M02-S03-P001", "type": "fact", "quote": "原文逐字片段"}]}
  ],
  "edges": [
    {"from": "n01", "to": "n02", "relation": "causes",
     "evidence": [{"unit": "M02-S05-P001"}], "note": ""}
  ]
}
```

- `kind`：root/question/background/method/evidence/conclusion/limitation/task/risk/concept/decision/action/milestone/variable/control/criteria/step/goal/dependency/deliverable/topic/group。
- `evidence.type`：fact（quote 逐字）/ summary / inference（节点须标 uncertain）。
- `edges.relation` 七类：causes/depends_on/contrasts/precedes/cites/supports/conflicts。
- 每个事实性节点挂 evidence；数字必须见于证据单元原文。

### Phase 3 审计

```bash
python3 $S/map_audit.py --work /app/work
```

读 `work/audit.json`，critical 必须修，修完重跑确认 critical=0。

### Phase 4 图集拆分与渲染

```bash
python3 $S/atlas.py --work /app/work --out /app/output
```

- 节点 ≤40：单图模式，渲染 overview.* 全套。
- 节点 >40：总览图（根+一级分支+各分支规模计数）+ 每个一级分支一张 topic_XX.* 详图
  （超预算分支自动截断到二级），并生成 `atlas_index.md` 与 `atlas.html` 导航。
- 每图含 md/mm/opml/mmd/svg/html（+png 若环境支持）；节点 id 全图集唯一稳定，evidence 单元号跨图一致。

### Phase 5 汇总与闸门

```bash
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "mindmap-atlas v1.0.3" --status success
python3 $S/validate_output.py --out /app/output --work /app/work
```

有未修复 critical、材料缺口或分支截断较多时 `--status partial`，并在 `work/uncertainty.json`
（JSON 数组）说明哪些分支被截断、原因与建议。

## 异常处置表

| 异常 | 处置 |
|-|-|
| 材料解析失败 | exceptions 已记录，用其余材料继续，uncertainty 标注 |
| 一级分支不均（某支 >100 节点） | 允许；引擎截断到二级并在索引标注，剩余信息在 mindmap.normalized.json 可查 |
| 分支间有交叉关系 | 用 edges 表达；同一张详图内的边随图渲染，跨图边保留在 normalized.json |
| 单图模式但任务要求分层 | 说明材料规模不足以拆分，属正常行为 |
| 预算过半 | 立即以当前 mindmap.json 跑 Phase 3-5，status=partial |

## 预算兜底

第 1 个响应完成 Phase 0；40 次请求前必须已进入 Phase 4；中断时 result.json 至少是骨架。
