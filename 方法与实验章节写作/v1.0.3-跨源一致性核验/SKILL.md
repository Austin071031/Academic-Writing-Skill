---
name: methods-cross-source-consistency
description: >-
  跨源一致性核验：配置/日志/代码/论文四处同一参数取值的一致性检测与三级裁决。当用户
  提供论文 PDF、配置、日志、代码等材料要求"撰写/补写方法与实验章节、核对参数是否与
  配置一致、检查章节数值有没有写错"时触发；亦适用于发现"配置文件写 A、日志实际跑 B、
  论文写 C"类矛盾需要裁决的场景。不触发：真实重跑实验、全文润色、文献管理。产出物：
  methods_chapter.md（七节成稿，取值经裁决）、consistency_report.json（裁决覆盖率）、
  conflicts.jsonl（候选冲突机检清单）、provenance_map.json、build_report.json 与
  result.json（含冲突裁决、人工确认项与不确定性）。
---

# v1.0.3｜跨源一致性核验（同参数四源取值，机检冲突 + 三级裁决）

核心分工：**引擎做冲突候选机检**（同名参数跨文件多值，数值归一化后比对：3e-4 = 0.0003）；
**Agent 做三级裁决**（日志实际运行值 > 配置实验意图 > 代码默认值 > 论文正文转述），
每项裁决写规则与理由；**引擎再做裁决覆盖率校验**（每个候选冲突必须被裁决或升级人工）。
专治"写得准"：章节里的每个取值都是经过对账的值，不是顺手抄的一个。

## 三条红线

1. **不回避冲突**：candidate conflict 必须逐项裁决（chosen_value+rule+rationale）或
   escalated 升级人工确认；unresolved 存在时 status 不得 success。
2. **不静默改值**：正文取值与配置不一致时，必须 changes.json 留痕说明采信哪个源、为何。
3. **不臆造**：裁决依据必须指向具体 eid；无材料佐证的取值不得进正文。

## 环境与路径约定

- 输入：`/input/case.json`、`/input/task.md`、材料文件（PDF/配置/日志/代码/文档）。
- 工作目录 `/app/work`，最终产物 `/app/output`（必须含 `result.json`）。
- 本 Skill 安装于 `/skills/weekly-skill`，命令一律绝对路径。
- 预算：64 次模型请求 / 900 秒 / 每响应 ≤16384 token；Phase 3 控制在 25 次请求内。

## Phase 0 — 落盘骨架

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
```

## Phase 1 — 侦查、抽取与冲突机检

```bash
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 /skills/weekly-skill/scripts/extract_evidence.py --work /app/work
python3 /skills/weekly-skill/scripts/cross_source_check.py --phase detect --work /app/work --out /app/output
```

读 `work/conflicts.jsonl`：每条 `{name, occurrences:[{value, eid, source}]}`。注意引擎已做数值
归一化（3e-4 与 0.0003 同组），同组多值才是实质冲突；异组多值多为笔误/单位差异，按规则处理。

## Phase 2 — 读本版本方法规则

1. `consistency_rules.md` —— 三级优先级、裁决格式、别名归并（lr/learning_rate）、
   豁免情形（笔误、单位换算、不同实验阶段）；
2. `six_elements_checklist.md`；3. `parameter_table_template.md`；
4. `gap_question_checklist.md`；5. `failure_modes.md`。

## Phase 3 — 裁决与行文（Agent 核心工作）

1. 写 `work/conflict_resolutions.json`：

```json
[{"name": "learning_rate", "chosen_value": "3e-4", "rule": "日志实际运行 > 代码默认",
  "rationale": "日志 E0013 记录运行值 0.0003（=3e-4）；代码默认 1e-3 被配置覆盖",
  "eids": ["E0005", "E0013", "E0015"]}]
```

无法判定的写 `{"name": "…", "escalated": true, "question_for_author": "…"}`。
2. 写七节正文：参数取值一律用裁决值并挂主证据锚点；被否决的取值不写进正文（可进附录C
   说明"某文件记为 X，经裁决未采用"）。
3. 写 `table_rows.json`、`gaps.json`、`changes.json`（每条取舍一条记录）、`status.json`、
   `contract_extra.json`。

## Phase 4 — 裁决校验、装配与校验

```bash
python3 /skills/weekly-skill/scripts/cross_source_check.py --phase verify --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/build_deliverables.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work --expect-status success
```

- verify fail（存在 unresolved）：回 Phase 3 补裁决或升级；全部 escalated 时 status=partial。

## Phase 5 — 如实定态

存在 escalated 冲突 → status="partial"，追问进 manual_confirmations；全部裁决 → "success"。
result.json 的 change_log 必须能看到每条取舍。

## 异常处置

| 情况 | 处置 |
|-|-|
| 只有单一来源，无机检冲突 | consistency_report 记 0 冲突，正常装配；不编造冲突 |
| 单位/写法差异（3e-4 vs 0.0003） | 归一化同组视为一致，changes 注明等价 |
| 不同实验阶段各有一套参数 | 裁决按阶段分别进行，scope 分开登记 |
| 日志与配置实质不同且无法判定 | escalated + gaps(high)，正文暂用配置值并标注"待确认" |
| 900 秒预算告急 | 立即跑 Phase 4 交付 partial |

## 最小调用示例

见 `examples/minimal_example.md`（合成材料，标注为示例）。
