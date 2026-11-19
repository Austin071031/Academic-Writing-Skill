---
name: mindmap-refine-loop
description: 迭代精炼式思维导图生成，主打"草稿→机检评分→按单修订"质量闭环。当用户要求从科研材料（论文/综述/方案/纪要/笔记）生成高质量思维导图，尤其强调覆盖完整、抓得准、可追溯时触发；无材料的开放脑图不触发。引擎按题面五问（抓得准/理得清/连得对/可追溯/实际有用）计算机检评分并给出按严重度排序的修复清单，Agent 按单修订一轮后交付六格式导图（md/mm/opml/mmd/svg/html）+ 五维评分报告 + 证据溯源 + result.json。
---

# 思维导图 Skill（迭代精炼闭环 · mindmap-refine-loop）

核心思想：**好导图是改出来的**。基础 Agent 一次成图、无法自评；本 Skill 用覆盖矩阵（每个材料单元 ↔ 最佳匹配节点）与五维 rubric 机检把"质量"变成可执行修复清单，一轮定向修订即可显著提升。

## 何时使用 / 不使用

- 使用：需要高覆盖率、高保真、可溯源的科研材料导图；时间预算允许一轮修订。
- 不使用：无材料脑图；或只要一份草稿不在乎质量核验。

## 运行时契约

- 输入 `/input/case.json`、`/input/task.md`、材料文件；工作目录 `/app/work`；产物 `/app/output`（`result.json` 含 output_contract 全部字段与 case_id）。
- 预算 64 请求 / 900 秒 / 16384 token；脚本目录记作 `$S` = `/skills/weekly-skill/scripts/`（以实际安装目录为准）。
- 仅用 Python3 标准库；无网络假设。

## 三条红线

1. 不得编造事实、数字、单元号；材料没有的内容标 `status="missing"`。
2. `type="fact"` 的 `quote` 必须是原文子串；数字必须见于证据单元。
3. refine 报告的问题不得隐瞒：逐条修复或写入 uncertainty 并如实 partial。

## 总流程

### Phase 0 落盘、勘察与解析

```bash
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_materials.py --work /app/work
```

读 `work/materials_digest.md` 掌握全局；需要原文按单元号到 `work/materials.json` 取。

### Phase 1 草稿（不要追求完美，快速成图）

写 `/app/work/mindmap.json`：

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

### Phase 2 机检评分（第一轮）

```bash
python3 $S/map_audit.py --work /app/work
python3 $S/refine.py --work /app/work
```

读两份报告：
- `work/audit.json`：硬错误（quote 非原文、单元号不存在、数字查无出处）。
- `work/refine_report.json` + `work/fix_list.md`：五维得分（抓得准/理得清/连得对/可追溯/实际有用）
  与按 critical→high→medium→low 排序的修复清单，包括**重要未覆盖单元**（含数字/标题/长段落
  却没有节点引用的材料单元）。

### Phase 3 定向修订（一轮，最多两轮）

按 fix_list.md 自上而下修：critical 全修 → high 全修 → medium 按预算。
修订后重跑：

```bash
python3 $S/map_audit.py --work /app/work
python3 $S/refine.py --work /app/work
```

把两轮得分（refine_report.json 的 scores/overall）写入 `work/stats.json`，例如
`{"refine_rounds": [{"overall": 72.1}, {"overall": 88.4}]}`——这是增益可验证证据。

### Phase 4 渲染与交付

```bash
python3 $S/map_render.py --work /app/work --out /app/output
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "mindmap-refine-loop v1.0.4" --status success
python3 $S/validate_output.py --out /app/output --work /app/work
```

同时把最终 `work/refine_report.json` 复制为 `/app/output/refine_report.json`（质量自证）。
有未修复 critical/high 时 `--status partial` 并写 `work/uncertainty.json`（JSON 数组）。

## 五维 rubric（引擎口径，修订时对照）

| 维度 | 引擎度量 | 修订动作 |
|-|-|-|
| 抓得准 | fact quote 原文命中率、数字溯源率 | 改 quote 为逐字；数字核对原文 |
| 理得清 | 深度/扇出、重复标题、同级 kind 混杂 | 合并、分组、统一分类维度 |
| 连得对 | 边证据率、词表合法率、孤立事实节点 | 补边挂证据；删无依据边 |
| 可追溯 | 证据节点率、材料覆盖率、重要单元覆盖 | 给事实节点挂 evidence；补重要单元节点 |
| 实际有用 | purpose/audience、kind 多样性、待确认标注 | 填元信息；标 uncertain/missing |

## 异常处置表

| 异常 | 处置 |
|-|-|
| 材料解析失败 | exceptions 已记录，用其余材料继续，uncertainty 标注 |
| 覆盖率低但材料本就冗余 | 在 uncertainty 说明"覆盖率受材料冗余影响"，勿为凑覆盖挂无关节点 |
| 修复与原文冲突 | 以原文为准，标 uncertain 并记录 |
| 两轮后仍有 high | 如实 partial，uncertainty 列出剩余项与建议 |
| 预算过半 | 跳过第二轮修订，直接 Phase 4，status=partial |

## 预算兜底

第 1 个响应完成 Phase 0；40 次请求前必须已进入 Phase 4；中断时 result.json 至少是骨架。
