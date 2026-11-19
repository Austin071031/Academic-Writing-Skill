---
name: contribution-evidence-alignment
description: >-
  贡献对得上：每条贡献条目必须能指回稿件中的方法/图表/具体数字，范围词（首次/最优/全面）
  须有比较性数据支撑否则转人工确认。当用户要求"写贡献点/核对贡献与结果是否一致/压缩贡献表述/
  写引言贡献段"时触发；亦适用于贡献夸大、贡献与实验结果脱节、贡献条数与正文证据不对应等
  写作与修复场景。不触发：相关工作分组、空白推导、引用格式维护等无关任务。
  产出物：contributions_check.md（贡献-证据对照表）、introduction.md、related_work.md、
  references.md、evidence_map.json、version_report.json、result.json（含 manual_confirmations）。
---

# v1.0.3｜贡献对得上（贡献卡片 + 证据位置核验 + 范围词防线）

核心机制：贡献不是形容词，是**可核对的卡片**。每条贡献在 work/contributions.json 中登记
{表述, 类型(method/experiment/conclusion), 证据位置[], 范围词[]}；引擎逐条核验：
证据位置必须能解析到稿件段落（P###）或图表（图N/表N 须出现在稿件中）、
贡献句中的每个数字必须能在证据位置文本中找到（数字可回溯）、
"首次/最优/全面/显著"等范围词若无可比较数据支撑则自动转 manual_confirmations（人工确认项）。

## 三条红线

1. **不夸大**：范围词只用稿件证据撑得起的；引擎检出的 overclaim_risk 必须人工确认或改写。
2. **每条贡献必有证据位置**：没有证据位置的贡献条目判 issues，修复或删除。
3. **不手写引用编号**：〔E#〕 锚点 + 引擎注入 [n]；数字必须与稿件一致。

## 环境与路径约定

- 输入 `/input/case.json`、`/input/task.md`、材料（稿件必须有方法/结果，否则贡献无法核验）。
- 工作 `/app/work`，产物 `/app/output`；命令用绝对路径。
- 预算：64 请求 / 900 秒；Phase 3 控制在 24 次请求内。

## Phase 0 — 落盘骨架

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
```

## Phase 1 — 侦查与解析

```bash
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 /skills/weekly-skill/scripts/parse_manuscript.py <稿件路径> --work /app/work
python3 /skills/weekly-skill/scripts/parse_library.py <文献库文件...> --work /app/work
python3 /skills/weekly-skill/scripts/parse_notes.py <笔记文件...> --work /app/work
python3 /skills/weekly-skill/scripts/extract_facts.py --work /app/work
```

重点读 manuscript.json 的方法/结果/图表段落与 figure_note/table_note（贡献证据源）。

## Phase 2 — 读规则

1. `contribution_method.md` —— 贡献压缩三原则（一条一证据、动词对齐类型、范围词克制）；
2. `scope_words.md` —— 范围词清单与替代写法；
3. `evidence_anchor_rules.md` —— 锚点与绑定细则；
4. `failure_modes.md` —— 贡献写作失败案例。

## Phase 3 — 判断与写作

### 3.1 本版本核心：/app/work/contributions.json

```json
{"items": [
  {"cid": "CT1", "statement": "提出湿化学 Li2O-LiNbO3 梯度缓冲层制备方法，在 8 nm 尺度实现成分梯度可控",
   "type": "method", "evidence_locs": ["P007"], "scope_words": []},
  {"cid": "CT2", "statement": "空气中暴露 24 小时后界面电阻仅增加 12%，对照组增加 210%",
   "type": "experiment", "evidence_locs": ["P003"], "scope_words": []},
  {"cid": "CT3", "statement": "全电池 200 次循环容量保持率达 91.3%",
   "type": "conclusion", "evidence_locs": ["P009", "表1"], "scope_words": []}
]}
```

- 3–5 条；每条 type ∈ method | experiment | conclusion。
- evidence_locs：P###（manuscript.json 的 pid）和/或 图N、表N（须能在稿件文本中找到）。
- scope_words：把表述里的评价词如实列出（如"首次""最优""显著"），供引擎检查。

### 3.2 draft_intro.md 贡献段

- 贡献段逐条对应 contributions.json：每条贡献一句话 + （证据位置）+ 〔E#〕。
- 模板："针对上述空白，本文提出 X。主要贡献：（1）……（方法，证据见 P007）；（2）……（实验，证据见 P003、图2）；……"
- 三组二级标题齐全：研究背景与问题 / 研究空白 / 本文贡献。

### 3.3 evidence_map.json（本文 result 类证据必须登记：每条贡献至少一条）

### 3.4 draft_rl.md + claim_bindings.jsonl（同共享口径）

### 3.5 不确定性与异常（按需；overclaim_risk 由引擎写入 manual_confirmations）

## Phase 4 — 引擎核验与构建

```bash
python3 /skills/weekly-skill/scripts/contribution_align.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/build_deliverables.py --work /app/work --out /app/output
```

- 读 output/contributions_check.md 与 work/version_report.json：每条 issues 空；
  scope_flags 为空或已全部进入 manual_confirmations；verdict=pass 最佳。
- 读 build_report.json：锚点全解析、绑定 ≥90%、四要素全 true、无手写编号。
- 允许一次修复循环；仍有问题如实降级。

收尾（必跑）：

```bash
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --case /input/case.json --skill "contribution-evidence-alignment v1.0.3" --status <success|partial>
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --expect-status <success|partial>
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```

## Phase 5 — 状态判定

- `success`：贡献 ≥1 条且全部 issues 空；build 四项全过（scope_flags 允许存在但须已登记人工确认）。
- `partial`：贡献缺失/不可核验但其余可用；写明缺口。
- 至少保留骨架 result.json 与工作稿副本。

## 异常处置表

| 情况 | 处置 |
|---|---|
| 稿件缺方法/结果（只有题目） | 贡献无法核验：贡献段写"计划贡献"并标 judgment，status=partial |
| 证据位置在稿件中找不到 | 引擎报 issues；核对 pid/图表编号后修复 |
| 贡献句数字在证据位置找不到 | 引擎报"数字不可回溯"；改正数字或换证据位置 |
| 范围词被标记 overclaim_risk | 改写为克制表述，或保留并确保进入 manual_confirmations |
| 绑定句定位失败 | 逐字核对修复；禁止手写编号 |
| 模型请求 >40 或耗时 >600s | 跳过修复循环直接收尾，status=partial |
| 英文任务 | 卡片结构不变；范围词清单按英文等价词（first/state-of-the-art/comprehensive）人工登记 |

## 交付物清单（/app/output）

contributions_check.md、introduction.md、related_work.md、references.md、evidence_map.json、
build_report.json、version_report.json、result.json（含 manual_confirmations）、preview.html。
