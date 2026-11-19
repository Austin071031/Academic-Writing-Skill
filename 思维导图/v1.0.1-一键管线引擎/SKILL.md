---
name: mindmap-pipeline-engine
description: 一键管线式思维导图生成。当用户要求从科研材料（论文/报告/方案/纪要/笔记）生成思维导图、知识结构图或研究框架图时触发；纯摘要写作、与材料无关的脑图不触发。Agent 只需产出一份 mindmap.json，管线引擎自动完成结构修复（扇出分组/深层提升）、溯源审计、六格式渲染、结果汇总与发布闸门，一条命令交付 /app/output 全部产物（md/mm/opml/mmd/svg/png/html + evidence_map + audit_report + result.json）。
---

# 思维导图 Skill（一键管线引擎 · mindmap-pipeline-engine）

核心思想：**Agent 只写一份 JSON，其余全部自动化**。相对基础 Agent 手工排版、手工核对，本管线把"修复→审计→渲染→汇总→闸门"压缩为一条命令，且所有自动修复记入 change_log 可复核。

## 何时使用 / 不使用

- 使用：给定科研材料需要可编辑、可溯源、带预览的思维导图交付。
- 不使用：无材料的开放式脑图；只要纯文本总结。

## 运行时契约

- 输入：`/input/case.json`、`/input/task.md` 与材料文件。
- 工作目录 `/app/work`；最终产物 `/app/output`（含 `result.json`，含 output_contract 全部字段与 case_id）。
- 预算：64 请求 / 900 秒 / 16384 token。脚本路径记作 `$S` = `/skills/weekly-skill/scripts/`（以实际安装目录为准）。
- 仅用 Python3 标准库；无网络假设。

## 三条红线

1. 不得编造事实、数字、单元号；材料没有的内容标 `status="missing"`。
2. `type="fact"` 的 `quote` 必须是原文子串；数字必须见于证据单元（脚本核验，造假必现 critical）。
3. 管线报 critical 不得隐瞒：修复后重跑，或接受引擎自动降级 partial 并写明 uncertainty。

## 总流程

### Phase 0 落盘与勘察

```bash
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_materials.py --work /app/work
```

读 `work/materials_digest.md` 掌握全局（单元号是溯源锚点）；需要原文按单元号到 `work/materials.json` 取。

### Phase 1 写 mindmap.json（Agent 唯一的创作步骤）

按任务用途（论文梳理/实验设计/项目计划/会议纪要/概念体系）组织 2–5 层树，
写入 `/app/work/mindmap.json`。字段规范：

```json
{
  "title": "导图标题", "purpose": "用途", "audience": "受众", "root": "root",
  "nodes": [
    {"id": "root", "title": "主题", "parent": null, "kind": "root",
     "note": "", "status": "confirmed", "evidence": []},
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
- `evidence.type`：fact（quote 逐字）/ summary（可改写）/ inference（节点须标 uncertain）。
- `edges.relation` 七类：causes/depends_on/contrasts/precedes/cites/supports/conflicts。
- 每个事实性节点必须挂 evidence；节点标题中的数字必须出现在其证据单元原文中。
- 不必担心扇出与深度——引擎会自动分组与提升（见 Phase 2），但逻辑分类仍由你负责。

### Phase 2 一键管线

```bash
python3 $S/engine.py run --work /app/work --out /app/output --case /input/case.json \
    --status success --skill "mindmap-pipeline-engine v1.0.1"
```

引擎依次执行：
1. **fix** 结构自动修复：扇出>7 按 kind/材料来源聚类插入分组节点；深度>6 自动上提（全部记 change_log）；
2. **map_audit** 溯源审计（quote 逐字核验、数字溯源、边证据、覆盖率）；
3. **map_render** 渲染 mindmap.md/.mm/.opml/.mmd/.svg/.html（+.png 若环境支持）；
4. **assemble_result** 汇总 result.json（自动回填 output_contract 字段）；
5. **validate_output** 发布闸门。

### Phase 3 看报告、必要时修订

- 读 `work/audit.json`：critical 必须修（改 mindmap.json 后重跑 Phase 2）；warning 尽量修。
- 引擎检测到 critical 时会自动把 status 降为 partial —— 这是诚实机制，不要强行 success。
- 有材料缺口/冲突时在 `work/uncertainty.json`（JSON 数组）补充说明后重跑 Phase 2。

## 异常处置表

| 异常 | 处置 |
|-|-|
| 材料解析失败 | exceptions 已记录，用其余材料继续，uncertainty 标注 |
| mindmap.json 语法错误 | 引擎退出并提示；用 `python3 -m json.tool` 定位后修正 |
| 审计 critical | 修 mindmap.json 重跑 Phase 2；无法修则 partial |
| PNG 未生成 | preview_status.json 已记录原因；SVG/HTML 仍是有效预览，不算失败 |
| 节点爆炸 | fix 已自动分组；若仍 >400 节点，合并叶节点后重跑 |
| 预算过半 | 立即以当前 mindmap.json 跑 Phase 2（哪怕只有骨架） |

## 预算兜底

第 1 个响应完成 Phase 0；请求用掉 40 次前必须已跑过至少一次 `engine.py run`。
中断时 result.json 至少是骨架，不会空手。
