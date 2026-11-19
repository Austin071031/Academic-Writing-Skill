---
name: mindmap-template-studio
description: 结构模板驱动的科研材料思维导图生成。当用户要求从论文、综述、实验方案、项目计划或会议纪要等科研材料整理思维导图/概念图/知识框架，或要求"梳理材料结构、提取研究问题-方法-证据-结论"时触发；不要求溯源、纯闲聊或与科研材料无关的脑图不触发。产出可编辑导图（Markdown 大纲 / FreeMind .mm / OPML / Mermaid）+ SVG/PNG/HTML 预览 + 逐节点证据溯源表 + 审计报告，全部落盘 /app/output 并汇总 result.json。
---

# 思维导图 Skill（结构模板驱动 · mindmap-template-studio）

核心思想：**先识别材料类型、套结构骨架，再逐槽位填充**。脚本承担解析、模板、审计、渲染等全部机械劳动；Agent 只做阅读、判断与填写。

## 何时使用 / 不使用

- 使用：给定科研材料（论文/综述/实验方案/项目计划/会议纪要/笔记），需要结构化思维导图，且要求节点可溯源、导图可继续编辑。
- 不使用：材料与科研无关；或用户只要一段概括文字而不要导图文件。

## 运行时契约

- 输入：`/input/case.json`、`/input/task.md` 与材料文件（md/txt/tex/html/docx/pdf 等）。
- 工作目录 `/app/work`；最终产物 `/app/output`，必须含 `result.json`（含 case.json `output_contract` 全部字段与 `case_id`）。
- 预算：64 次模型请求、900 秒、16384 token/响应。**先落盘、后完善**，超时也要交出诚实部分结果。
- 脚本路径：`/skills/weekly-skill/scripts/`（若实际安装目录不同，以实际目录为准，下文统一记作 `$S`）。
- 仅用 Python3 标准库；无网络假设。

## 三条红线

1. 不得编造材料中不存在的事实、数字、引用；材料没有的内容标 `status="missing"`。
2. `type="fact"` 的证据 `quote` 必须是该单元原文子串；数字必须能在证据单元中找到（脚本会核验，造假必被审计标 critical）。
3. 任何脚本核验失败不得隐瞒：修复或如实降级 `status="partial"` 并在 uncertainty 中说明。

## 总流程

### Phase 0 落盘与勘察（必须最先做）

```bash
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
```

读 `/app/work/inspection.json`：确认 case_id、材料清单、output_contract、用途/受众线索。

### Phase 1 材料解析

```bash
python3 $S/parse_materials.py --work /app/work
```

产出 `work/materials.json`（全部单元，含原文）与 `work/materials_digest.md`（压缩目录）。
**Agent 先读 digest 掌握全局**，需要某段原文时再到 materials.json 按单元号取（节省 token）。
解析失败的材料已在 exceptions.json 记录，不要重试超过一次。

### Phase 2 模板识别与骨架生成

```bash
python3 $S/templates.py --work /app/work
```

产出 `work/skeleton.json`（导图骨架，槽位节点 status="missing"）与 `work/slot_checklist.md`（逐槽位填写清单）。
若判定类型与任务明显不符，以任务说明为准改用通用六分支（见 references/templates.md）。

### Phase 3 填图（Agent 的核心工作）

把 `skeleton.json` 复制改写为 `work/mindmap.json`：

- 用材料中的真实内容替换/扩展每个槽位节点，可在槽位下自由加子节点（建议 2–5 层）。
- 每个**事实性**节点挂 evidence；组织性节点（纯分类标题）可不挂。
- 材料没有的分支保留槽位节点并标 `status="missing"`，不确定的标 `"uncertain"`。
- 有因果/对比/依赖/时间/引用/支持/冲突关系时在 `edges` 中显式连边并挂证据。

`mindmap.json` 规范（严格遵守，字段缺一不可）：

```json
{
  "title": "导图标题", "purpose": "用途", "audience": "受众", "root": "root",
  "nodes": [
    {"id": "root", "title": "主题", "parent": null, "kind": "root",
     "note": "可选备注", "status": "confirmed", "evidence": []},
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

- `kind` 词表：root/question/background/method/evidence/conclusion/limitation/task/risk/concept/decision/action/milestone/variable/control/criteria/step/scope/taxonomy/schools/consensus/debate/gap/goal/dependency/deliverable/topic/group。
- `evidence.type`：`fact`（quote 必须原文逐字）/ `summary`（允许改写，quote 可省）/ `inference`（推断，节点必须同时标 uncertain）。
- `edges.relation` 七类：causes / depends_on / contrasts / precedes / cites / supports / conflicts。
- 单元号取自 digest，如 `M01-S02-P003`；页码由脚本自动带出。

### Phase 4 审计与修订

```bash
python3 $S/map_audit.py --work /app/work
```

读 `work/audit.json`：critical 必须修复（证据单元不存在、quote 非原文、数字查无出处、空标题）；
warning 尽量修（扇出>9、缺证据的边、重复标题）。修完**重跑一次** map_audit.py 确认 critical=0。
规范化修复（id 重名、父节点悬空等）脚本已自动完成并记入 change_log。

### Phase 5 渲染与交付

```bash
python3 $S/map_render.py --work /app/work --out /app/output
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "mindmap-template-studio v1.0.0" --status success
python3 $S/validate_output.py --out /app/output --work /app/work
```

- 交付物：`mindmap.md/.mm/.opml/.mmd`（四种可编辑源）+ `mindmap.svg/.png/.html`（预览）
  + `evidence_map.json` + `audit_report.json` + `result.json`。
- 有未修复 critical 或材料部分缺失时 `--status partial`，并在 `work/uncertainty.json`
  （JSON 数组，如 `[{"item":"…","reason":"…","suggestion":"…"}]`）写明。
- validate_output.py 不通过时按提示修复后重跑 Phase 5；不要绕过闸门。

## 异常处置表

| 异常 | 处置 |
|-|-|
| 材料解析失败（PDF 扫描件等） | 记录 exceptions，用其余材料继续，uncertainty 标注 |
| 材料过短/无实质内容 | 导图照做，相关槽位标 missing，status=partial |
| 材料间数字/结论冲突 | 两个节点并列 + conflicts 边，双方各挂证据，标 uncertain |
| 单元号对不上 | 回 digest 重新定位，禁止凭空填写 unit |
| 节点爆炸（>60） | 合并同类叶节点，保证深度≤6、扇出≤9 |
| 请求预算过半仍在 Phase 3 | 立即以当前 mindmap.json 跑 Phase 4-5，status=partial |

## 预算兜底

第 1 个响应内必须完成 Phase 0-1；模型请求用掉 40 次前必须已进入 Phase 5。
任何时候中断，`/app/output/result.json` 至少是 init_result 骨架，不会空手。
