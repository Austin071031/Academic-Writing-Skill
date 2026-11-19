---
name: research-gap-derivation
description: >-
  研究空白说得实：空白必须由已引文献的缺口或材料矛盾显式推导。当用户要求"写研究空白/
  推导研究空白/写引言（含空白段）/论证选题必要性"，或需要把"本文做什么"与"已有工作缺什么"
  一一对应时触发；亦适用于空白段空泛（"少有研究""尚不充分"却无据）的写作与修复场景。
  不触发：相关工作分组（见 related-work-grouping）、引用格式维护、结果复现等无关任务。
  产出物：gap_derivation.md（前提→缺口→本文对应推导链）、introduction.md、related_work.md、
  references.md、evidence_map.json、version_report.json、result.json。
---

# v1.0.2｜研究空白说得实（空白推导链 + 数字泄漏防线）

核心机制：**空白不许"感觉式"书写**。每条空白在 work/gap_chain.json 中登记为
"前提（已引文献/材料的具体限制，含摘录）→ 缺口陈述 → 本文对应（含证据位置）"三元结构；
引擎校验每条前提可溯源（entry_ids 或稿件段落）、强制数字泄漏检查
（空白与对应句中的每个数字必须能在前提摘录或稿件证据位置中找到），并渲染推导链报告。
材料推不出空白时，引擎判 fail——必须改为如实标注或 status=partial，不得硬写。

## 三条红线

1. **不臆造缺口**：前提的 limitation 与 quote 必须逐字来自笔记/稿件；gap_statement 只能是
   前提的逻辑结论，不得引入新材料外数字。
2. **不空喊"少有研究"**："研究较少/尚不充分"类表述必须绑定具体前提，否则删除。
3. **不手写引用编号**：〔E#〕 锚点 + 引擎注入 [n]。

## 环境与路径约定

- 输入 `/input/case.json`、`/input/task.md`、材料（稿件/文献库/笔记，格式同前）。
- 工作 `/app/work`，产物 `/app/output`；命令用绝对路径 `python3 /skills/weekly-skill/scripts/xxx.py`。
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

读 inspection.json 与 fact_candidates.jsonl；特别收集 limitation 类候选（extract_facts 已标 suggested_use）。

## Phase 2 — 读规则

1. `gap_derivation_method.md` —— 三种推导模式（共同限制/未覆盖场景/结论冲突）与三元结构写法；
2. `evidence_anchor_rules.md` —— 锚点与绑定细则；
3. `failure_modes.md` —— 空白写作失败案例。

## Phase 3 — 判断与写作

### 3.1 本版本核心：/app/work/gap_chain.json

```json
{"gaps": [
  {"gid": "GAP1",
   "premises": [
     {"entry_ids": ["R002"], "limitation": "均质 LiNbO3 包覆在 24 小时以上长时暴露下保护层开裂，长期稳定性不足",
      "quote": "24 小时以上长时暴露下保护层出现裂纹，长期稳定性仍不足"},
     {"entry_ids": ["R004"], "limitation": "梯度缓冲概念未考察干空气工况，放大工艺未验证",
      "quote": "200 次循环容量保持率 82%；未考察干空气工况"}
   ],
   "gap_statement": "兼顾长时空气稳定性与产线兼容性的表面工程方案仍存在空白",
   "paper_response": "本文的梯度缓冲层在 24 小时空气暴露后界面电阻仅增加 12%，且湿化学成本与现有产线兼容",
   "response_evidence_loc": "P003"}
]}
```

- 每条空白 ≥1 条前提；每条前提给 entry_ids（library 存在）或 manuscript_loc（稿件段落存在），且 quote 为材料摘录。
- 空白 1–3 条；优先合并为一条主空白 + 可选子空白。
- 三种推导模式任选其一：共同限制（多数已引工作共有的局限）、未覆盖场景（材料中明确没人做的场景）、
  结论冲突（两篇结论相互矛盾）。
- 推不出（笔记无 limitation、材料单薄）：不要硬写——写空 gaps 数组，把理由写入 uncertainty.json，
  引言空白段以"作者判断"明示，status=partial。

### 3.2 draft_intro.md（空白段必须与 gap_chain 一致）

- "研究空白"段落的每个缺口句，对应 gap_chain 一条记录；句末挂 〔E#〕（指向 limitation 证据）。
- 空白句模板："已有工作在 X 条件下取得 Y（前提概述），但 Z（共同限制）〔E#〕；因此，Q（缺口）仍是空白。"
- 结构仍含三组二级标题：研究背景与问题 / 研究空白 / 本文贡献。

### 3.3 evidence_map.json（每条前提的 limitation 与本文 result 必须登记；8–20 条）

### 3.4 draft_rl.md + claim_bindings.jsonl（同共享口径；相关工作为空白提供前提，转述要准）

### 3.5 不确定性与异常（uncertainty.json / exceptions.json 按需）

## Phase 4 — 引擎核验与构建

```bash
python3 /skills/weekly-skill/scripts/gap_chain.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/build_deliverables.py --work /app/work --out /app/output
```

- 读 output/gap_derivation.md 与 work/version_report.json：每条空白 issues 为空；number_leaks 为空；
  verdict=pass 最佳，warn 需修复，fail 必须处理（改推导或降级）。
- 读 build_report.json：锚点全解析、绑定 ≥90%、四要素全 true、无手写编号。
- 允许一次修复循环；仍有问题如实降级。

收尾（必跑）：

```bash
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --case /input/case.json --skill "research-gap-derivation v1.0.2" --status <success|partial>
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --expect-status <success|partial>
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```

## Phase 5 — 状态判定

- `success`：≥1 条空白且全部无 issues；build 四项全过。
- `partial`：空白缺失/有泄漏但其余可用；或材料不足以推导（gaps 空 + uncertainty 说明）。
- 至少保留骨架 result.json 与工作稿副本。

## 异常处置表

| 情况 | 处置 |
|---|---|
| 笔记无 limitation 摘录 | 从题名/结论反推时需写明 uncertainty（推断来源），并在 premise quote 给出最接近的材料原句 |
| 前提的文献在库中不存在 | 引擎报 issues；补入库或改引现有条目 |
| 空白句含材料外数字 | 引擎报 number_leaks；删除该数字或补前提 |
| 多篇结论相互冲突 | 用冲突模式：两条前提并列，quote 各给一句 |
| 绑定句定位失败 | 逐字核对修复；禁止手写编号 |
| 模型请求 >40 或耗时 >600s | 跳过修复循环直接收尾，status=partial |
| 英文任务 | 推导链结构不变；gap_statement 用英文 |

## 交付物清单（/app/output）

gap_derivation.md、introduction.md、related_work.md、references.md、evidence_map.json、
build_report.json、version_report.json、result.json、preview.html。
