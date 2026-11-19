---
name: related-work-grouping
description: >-
  相关工作分得清：按问题设定/方法路线分组并在同一维度上比较。当用户提供文献库与论文底稿，
  要求"整理相关工作 / 写文献综述 / 起草相关工作部分 / 比较已有方法"时触发；亦适用于修复
  相关工作逐篇罗列、按时间排序、分组遗漏关键工作、转述与原文不符等问题的场景。
  不触发：引用编号维护、文献去重、全文润色、引言背景单独修改等与"分组比较"无关的任务
  （背景方向见 intro-background-grounding）。
  产出物：related_work.md（按分组小节成稿）、comparison_matrix.md（五维比较矩阵）、
  introduction.md、references.md、evidence_map.json、version_report.json、result.json。
---

# v1.0.1｜相关工作分得清（按路线分组 + 五维比较矩阵）

核心机制：**Agent 判断分组与比较内容**（主题命名、逐工作五维填写、组内比较句），
**引擎保证分组完整性**（引用条目 ↔ 分组双向一致、无重复无遗漏）、**检测逐篇罗列/时间序**、
**渲染比较矩阵**。相关工作不许按年份排队：引擎会把"多句以年份开头"与"单句成段逐篇罗列"标为嫌疑。

## 三条红线

1. **不臆造文献与结论**：比较矩阵的每个格子、正文每句转述，必须来自 library.json 条目或笔记摘录；
   转述数字须与 evidence_map quote 一致。
2. **不手写引用编号**：正文只写 〔E#〕 锚点；`[n]` 由 build_deliverables.py 按首次出现顺序注入。
3. **分组必须覆盖全部引用**：被正文引用的每条文献必须落入恰好一个分组；引擎校验并渲染未入组清单。

## 环境与路径约定

- 输入 `/input/case.json`、`/input/task.md`、材料（文献库 bib/ris/enw/csv/json/GB-T 文本；稿件 md/txt/tex/docx/pdf；笔记 md/txt/json）。
- 工作 `/app/work`，产物 `/app/output`；Skill 位于 `/skills/weekly-skill`，命令用绝对路径。
- 预算：64 请求 / 900 秒；Phase 3 控制在 24 次请求内。

## Phase 0 — 落盘骨架

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
```

## Phase 1 — 侦查与解析

```bash
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
```

读 `work/inspection.json`，确认材料清单、语言、样式、output_contract。

```bash
python3 /skills/weekly-skill/scripts/parse_manuscript.py <稿件路径> --work /app/work
python3 /skills/weekly-skill/scripts/parse_library.py <文献库文件...> --work /app/work
python3 /skills/weekly-skill/scripts/parse_notes.py <笔记文件...> --work /app/work
python3 /skills/weekly-skill/scripts/extract_facts.py --work /app/work
```

文献库为空 → 无法完成相关工作，按异常表降级。

## Phase 2 — 读规则

1. `grouping_method.md` —— 分组步骤与命名规范；
2. `comparison_dimensions.md` —— 五维比较口径（问题设定/方法路线/数据与评价/主要结论/局限）；
3. `evidence_anchor_rules.md` —— 锚点与绑定细则（与共享口径一致）；
4. `failure_modes.md` —— 逐篇罗列等失败案例对照。

## Phase 3 — 判断与写作

### 3.1 evidence_map.json（同共享口径；8–20 条，含 finding/limitation/meta）

### 3.2 本版本核心 A：/app/work/grouping.json

```json
{"groups": [
  {"gid": "G1", "theme": "分解机理与综述", "dimension_focus": "问题设定与研究脉络",
   "entry_ids": ["R001", "R007"], "note": "确立问题与评价口径，不提供工程方案"}
]}
```

- theme 按方法路线或问题设定命名（如"均质包覆路线""端到端方法""基于 X 的路线"），禁止"早期工作""近期研究"这类时间命名。
- 每条被引文献入且仅入一个组；建议 2–4 组。
- dimension_focus 写明本组比较所沿的维度（问题设定/方法路线/数据与评价 中至少两个）。

### 3.3 本版本核心 B：/app/work/comparison_rows.jsonl（逐条五维比较，每行一条 JSON）

```json
{"entry_id": "R002", "problem_setting": "湿空气界面劣化", "method_route": "5 nm LiNbO3 均质包覆",
 "data_eval": "阻抗增长降 65%", "conclusion": "短时有效", "limitation": "24 小时以上保护层开裂"}
```

- 每个**被引用**的 entry 一行；内容来自笔记/条目，限 60 字内/格；禁止臆造。
- 允许缺行（引擎标注），但关键条目（每组内被重点转述者）必须填写。

### 3.4 draft_rl.md（相关工作工作稿）

```markdown
# 相关工作

## <theme1>
<组内比较句（同维度上的取舍），随后逐工作准确转述结论与局限，句末挂 〔E#〕。>

## <theme2>
...
```

- 每组先比较后转述；每组 ≥2 个被引工作（单工作组并邻组）。
- 篇幅 400–1000 字；最后可用一小节"与本文工作的比较"承接引言。

### 3.5 draft_intro.md（引言工作稿，同共享口径：背景/空白/贡献三组标题）

### 3.6 claim_bindings.jsonl（论断-引用绑定）

- rl 部分每条转述句一条 binding；claim_type 用 others_result/quantitative_fact/survey_coverage/comparison。
- intro 部分同共享口径。

### 3.7 不确定性与异常（按需写 uncertainty.json / exceptions.json）

## Phase 4 — 引擎核验与构建

```bash
python3 /skills/weekly-skill/scripts/group_related_work.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/build_deliverables.py --work /app/work --out /app/output
```

- 读 `output/comparison_matrix.md` 与 work/version_report.json：
  ungrouped_cited 必须为空；duplicates 为空；chronological_suspect 为空；verdict=pass 最佳。
- 读 `output/build_report.json`：锚点全解析、绑定 ≥90%、四要素全 true、agent_pre_numbered 为空。
- 允许一次修复循环；仍有问题如实降级。

收尾（必跑）：

```bash
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --case /input/case.json --skill "related-work-grouping v1.0.1" --status <success|partial>
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --expect-status <success|partial>
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```

## Phase 5 — 状态判定

- `success`：ungrouped/duplicates/chronological 全空，verdict ∈ {pass, warn}，build 四项全过。
- `partial`：任一项不满足但稿件可用；写明缺口。
- 至少保留骨架 result.json 与已写出工作稿副本。

## 异常处置表

| 情况 | 处置 |
|---|---|
| 文献库为空 | 相关工作无法核验转述；仅依笔记写综述并标 uncertainty，partial |
| 笔记缺失 | 比较格子以文献条目信息+稿件引用处为准，格子可标"—（未填写）" |
| 分组后仍有未入组引用 | 引擎列出 ungrouped_cited；并入最近组或新建组后重跑 |
| 两组主题高度重叠 | 合并为一组并在 note 说明取舍 |
| 绑定句定位失败 | 逐字核对修复；禁止手写编号绕过 |
| 模型请求 >40 或耗时 >600s | 跳过修复循环直接收尾，status=partial |
| 英文任务 | 分组与矩阵用英文；规则不变 |

## 交付物清单（/app/output）

related_work.md、comparison_matrix.md、introduction.md、references.md、evidence_map.json、
build_report.json、version_report.json、result.json、preview.html。
