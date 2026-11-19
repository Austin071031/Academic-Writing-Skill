---
name: citation-coverage-audit
description: >-
  引用覆盖对得上：关键/代表/近期工作分类覆盖审计 + 论断-引用双向绑定一致性。
  当用户要求"补引用/核对引用覆盖/检查该引未引/审校引言与相关工作的引用/整理参考文献"时触发；
  亦适用于引用悬空（正文[n]与文献表不一致）、关键工作漏引、近期进展缺失、引用堆在段末等
  问题的审计与修复场景。不触发：纯格式转换（GB/T↔APA）、文献去重合并、分组写作等无关任务。
  产出物：coverage_report.md（覆盖审计报告）、introduction.md、related_work.md、references.md、
  evidence_map.json、version_report.json、result.json（含 manual_confirmations）。
---

# v1.0.4｜引用覆盖对得上（角色分类覆盖 + 双向绑定审计）

核心机制：**引用不是装饰，是覆盖证据**。Agent 为文献库每条记录给出角色分类
（foundation/key/representative/recent/context/other + 理由）；引擎执行三类审计：
（1）分类完整性（每条入库记录必分类、理由充分）；
（2）论断-引用双向绑定（被引条目每条至少支撑一条论断；每条论断至少绑定一条文献；
group_overview 类论断要求 ≥2 条）；
（3）覆盖充分性（关键/代表/奠基条目漏引、近三年进展覆盖不足，自动转人工确认）。
引用编号仍由共享引擎按首次出现注入，validate_output 再做正文-文献表双向一致性复检。

## 三条红线

1. **不臆造文献**：entry_ids 只能来自 library.json；分类理由必须指向材料事实。
2. **不让论断裸奔**：正文每个事实性论断句都要有 binding；引擎把"未绑定文献的论断"列成
   naked_claims，必须修复或改标 transition。
3. **不手写引用编号**：〔E#〕 锚点 + 引擎注入 [n]。

## 环境与路径约定

- 输入 `/input/case.json`、`/input/task.md`、材料（文献库必备；稿件/笔记强烈建议）。
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

## Phase 2 — 读规则

1. `coverage_taxonomy.md` —— 角色分类口径与覆盖判据；
2. `binding_rules.md` —— 双向绑定细则（claim_type 选择、group_overview 要求）；
3. `evidence_anchor_rules.md` —— 锚点与绑定字段细则；
4. `failure_modes.md` —— 引用类失败案例。

## Phase 3 — 判断与写作

### 3.1 本版本核心 A：/app/work/ref_classification.jsonl（每行一条）

```json
{"entry_id": "R001", "role": "foundation", "rationale": "分解机理奠基综述，确立问题与研究脉络"}
{"entry_id": "R004", "role": "key", "rationale": "最接近的梯度概念工作，直接支撑空白推导"}
{"entry_id": "R006", "role": "recent", "rationale": "2024 年工艺窗口定量工作，支撑产线兼容性论述"}
```

- 覆盖 library.json 全部记录；role ∈ foundation | key | representative | recent | context | other；
  rationale ≥6 字，指向材料事实（笔记摘录/题名/年份）。

### 3.2 本版本核心 B：claim_bindings.jsonl（论断-引用绑定，逐句登记）

- 每个含他人结论/数字/方法转述的论断句一条：claim_type ∈ others_result | quantitative_fact |
  method_lineage | survey_coverage | comparison | own_result。
- 综述性概括句（覆盖一组文献）用 claim_type=group_overview 且 entry_ids ≥2。
- 纯过渡句不写 binding（引擎不会将其计入 naked_claims；若写了 binding 则 entry_ids 不能为空）。

### 3.3 draft_intro.md + draft_rl.md + evidence_map.json（同共享口径）

写作时对照 coverage 目标：关键工作必引、代表路线各有覆盖、近三年至少 1–2 篇。

### 3.4 不确定性与异常（按需）

## Phase 4 — 引擎核验与构建

```bash
python3 /skills/weekly-skill/scripts/coverage_audit.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/build_deliverables.py --work /app/work --out /app/output
```

- 读 output/coverage_report.md 与 work/version_report.json：
  classification_issues 为空；naked_claims 为空；uncovered_key_works 为空或已全部进
  manual_confirmations；recent.ratio ≥ 1/3；verdict=pass 最佳。
- 读 build_report.json：锚点全解析、绑定 ≥90%、四要素全 true、agent_pre_numbered 为空。
- 允许一次修复循环（补引/补分类/改 claim_type 后重跑）。

收尾（必跑）：

```bash
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --case /input/case.json --skill "citation-coverage-audit v1.0.4" --status <success|partial>
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --expect-status <success|partial>
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```

## Phase 5 — 状态判定

- `success`：分类全覆盖、无 naked_claims、build 四项全过（漏引提示允许存在但须已登记人工确认）。
- `partial`：文献库为空或绑定严重不足；写明缺口。
- 至少保留骨架 result.json 与工作稿副本。

## 异常处置表

| 情况 | 处置 |
|---|---|
| 文献库为空 | 无法引用；相关工作只能依据笔记，status=partial 并说明 |
| 笔记缺失无法判定角色 | role 标 other，rationale 写"依据题名与年份推断"，并登记 uncertainty |
| naked_claims 检出 | 补 binding（选对 claim_type），或确认该句为过渡句后从 bindings 删除 |
| 关键工作漏引 | 在相关工作相应分组补转述句 + binding；若刻意不引，须进 manual_confirmations |
| 绑定句定位失败 | 逐字核对修复；禁止手写编号 |
| 模型请求 >40 或耗时 >600s | 跳过修复循环直接收尾，status=partial |
| 英文任务 | 分类与绑定结构不变 |

## 交付物清单（/app/output）

coverage_report.md、introduction.md、related_work.md、references.md、evidence_map.json、
build_report.json、version_report.json、result.json（含 manual_confirmations）、preview.html。
