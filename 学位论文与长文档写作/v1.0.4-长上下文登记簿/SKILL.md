---
name: longdoc-dossier
description: 学位论文与长文档写作——长上下文登记簿与重复论述防护。当任务要求在数万字规模的分章节长文档中续写/新写章节，且需要保持对前文定义、已用材料、已下结论的可见性（前文一致性）、避免后写章节与前文脱节或重复论述，或需要为写作生成受字数预算约束的上下文摘要时触发。不触发：单篇短文写作、纯文献格式转换、无需参考前文/材料的独立写作。产出物：dossier.json/.md（上下文登记簿）、context_brief.md（写作上下文摘要）、overlap_report.json/.md（重复/脱节/遗漏复核）、新章节稿与 result.json。
---

# 学位论文与长文档写作：长上下文登记簿与重复论述防护（v1.0.4）

## 0. 用途与适用条件

- 输入：`/input/case.json`、`/input/task.md`、分章节工作稿（`/input/**`，md/txt/tex/docx/pdf）、
  事实材料/笔记（文件名含 facts/notes/material/材料/笔记/数据 等）、大纲、文献库。
- 输出：`/app/output` 下的新章节稿、上下文登记簿与复核报告、`result.json`
  （含 case.json `output_contract` 全部字段）。
- 核心问题（题面「写得长不脱节」）：数万字长文档读不进一次模型上下文（预算 64 次请求、
  单次响应 16384 token）。本 Skill 把全文压缩为**登记簿（dossier）**：定义、已下结论、
  材料使用矩阵、术语首现表；写作时 Agent **只读按预算生成的 context_brief，全程不需要
  通读全文**——这是效率增益的核心机制；写完后用 overlap 复核重复论述/重复结论/脱节/
  材料遗漏，保证后写章节与前文不脱节、不重复。

## 1. 三条红线

1. **不臆造前文定义**：章节中使用的缩写与术语，必须能在 `dossier.json` 的
   `definitions`/`glossary_first_use` 或本稿自身的定义句中找到出处；找不到就按
   「脱节」处理（补定义或改用全称），不得凭记忆虚构前文定义内容。
2. **不臆造核验结果**：`overlap` 未跑出 CLEAN/PASS_WITH_REMINDERS 不得声称「无重复、
   无脱节」；检出的 critical 项必须修复后复跑，或如实降级 `status="partial"` 并登记。
3. **脱节项不静默、必须标注**：凡 overlap 检出的未定义缩写、悬空图表引用、
   重复论述/重复结论，要么修复，要么在 `work/manual_confirmations.json` /
   `uncertainty.json` 中逐条登记理由；禁止悄悄放过。

## 2. 阶段流程（Phase 0-5）

所有命令中的 `/skills/weekly-skill` 为 Skill 安装目录。工作目录 `/app/work`，
产物目录 `/app/output`。

**Phase 0 — 初始化（防超时空手，必须先做）**

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md \
  --input-dir /input --work /app/work
```
Agent 动作：读 `work/inspection.json`，确认 case_id、章节稿候选
（`manuscript_candidates`）、材料/笔记候选（`notes_candidates`）、大纲与工单；
在 `work/task_notes.md` 用不超过 20 行记录：待写章节（目标 section 标题）、
必须沿用的术语要求、材料覆盖要求。

**Phase 1 — 解析材料**

```bash
python3 /skills/weekly-skill/scripts/parse_chapters.py <章节文件...> <材料文件...> --work /app/work
```
章节文件在前、材料文件在后一次传入。确认输出段落数与总字数合理；
解析 issues 非空 → 记入 `work/exceptions.json`（格式 `[{item, reason, severity}]`）。

**Phase 2 — 构建登记簿 + 生成写作上下文摘要**

```bash
python3 /skills/weekly-skill/scripts/dossier_engine.py build \
  --chapters /app/work/chapters.json --work /app/work
# 若材料文件名不含 fact/note/material/材料/笔记 等提示词，用 --materials-regex 显式指定
python3 /skills/weekly-skill/scripts/dossier_engine.py brief \
  --dossier /app/work/dossier.json --target-section "<目标章节标题>" \
  --budget-chars 3000 --work /app/work
```
产出：`work/dossier.json` + `work/dossier.md`（definitions / conclusions /
material_usage + omissions / glossary_first_use / captions），
`work/context_brief.md`（按目标章节相关性排序、受预算约束、如实记录截断量）。
Agent 动作：读 `context_brief.md`（**不需要读全文**，全文已由引擎压缩进登记簿）；
确认 brief 中定义、结论、未用材料提醒三类内容齐备；若某类为空且不合理
（如全文确无定义句），在 `work/exceptions.json` 登记。

**Phase 3 — 只读 brief 撰写新章节（Agent 写作）**

撰写规则（完整判据见 references/dossier_rules.md）：
- 术语与缩写一律沿用 brief「前文相关定义」中的写法；brief 未列出的新缩写必须在
  本稿首次出现处给出「全称（英文, ABBR）」定义；
- brief「前文已下结论」中的论断不得当作新结论重复宣称，引用时写「如第N章所述」；
- brief「已被前文使用的材料」如需引用，换论证角度复述，不得整句照搬；
- brief「未用材料提醒」中与本节相关的材料应尽量纳入（这是遗漏防护）；
- 新图/表编号接 brief「已有图表 caption」清单后续编；
- 每个事实句可溯源到材料段落（内部标注 `(来源: pid)`，定稿前转正文表述）。

把成稿写入 `/app/work/draft_<章节名>.md`。

**Phase 4 — 重叠/脱节复核（overlap）**

```bash
python3 /skills/weekly-skill/scripts/dossier_engine.py overlap \
  --draft /app/work/draft_<章节名>.md --chapters /app/work/chapters.json \
  --dossier /app/work/dossier.json --work /app/work
```
产出 `work/overlap_report.json/.md`，四类检查（判据见 references/dossier_rules.md）：
(a) 重复论述（句子级 4-gram Jaccard ≥0.6）；(b) 重复结论（同主语+共享关键数值）；
(c) 脱节（未定义缩写 critical/warning 分级 + 悬空图表引用）；
(d) 未用材料提醒（omissions 与草稿最相关段落 2-gram Jaccard ≥0.1）。
Agent 动作：**critical 项（重复论述/重复结论/critical 未定义缩写/悬空图表）必须
清零**——修复后复跑 overlap；warning 与材料提醒逐条判断，不采纳的在
`work/manual_confirmations.json` 写明理由。verdict 目标：
`CLEAN` 或 `PASS_WITH_REMINDERS`；达不到则 Phase 5 降级 `status="partial"`。

**Phase 5 — 交付**

```bash
cp /app/work/draft_<章节名>.md /app/output/chapter_<N>.md
cp /app/work/dossier.md /app/work/context_brief.md /app/work/overlap_report.md /app/output/
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output \
  --case /input/case.json --skill "longdoc-dossier v1.0.4" --status success|partial
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```
Agent 动作：把最终 overlap 计数、brief 截断量写入 `work/stats.json`；
论断-来源映射写入 `work/evidence_map.json`；章节新增/修改写入
`work/change_log.json`。validate 不通过 → 修复或如实降级 status。

## 3. 预算兜底

模型请求超过 40 次或剩余时间不足 1/3 时：跳过 Phase 3 的润色迭代与 Phase 4 的
修复循环，直接以当前 draft 跑一次 overlap 并进入 Phase 5，`status="partial"`，
`stats.json` 记录 `budget_fallback=true` 与未清零的 critical 项。骨架 result.json
已在 Phase 0 落盘，绝不空手。

## 4. 异常处置表

| 情况 | 处置 |
|-|-|
| case.json 缺失/损坏 | init_result 记录异常；inspect 继续；case_id="unknown"，result 如实标注 |
| 章节稿全部缺失/解析失败 | 无法建登记簿 → 仅交付任务分析与写作建议，status=partial，exceptions 登记 |
| 材料文件识别为空（build 警告） | 用 `--materials-regex` 按实际文件名重跑 build；仍无则 material_usage/omissions 为空并在 brief 截断记录中如实体现 |
| dossier 中定义/结论为空 | 不臆造：brief 对应节显示「（无）」，Agent 在 exceptions 登记「全文无显式定义句」，写作时按首次出现补定义 |
| brief 预算过小导致大量截断 | 提高 `--budget-chars`（≤8000）重跑；截断量始终如实记录在 brief 末尾 |
| overlap 检出 critical 但无法修复（如必须复述实验步骤） | 在 manual_confirmations 逐条登记理由，status=partial，不静默 |
| draft 文件缺失/不可读 | overlap 退出码 2；检查路径后重跑，不跳过复核直接交付 |
| docx/pdf 提取降级 | parse_chapters 记录 issues；该文件不进入证据池，exceptions 登记 |
| 编号/术语与工单要求冲突 | 以 dossier 登记的前文实际用法为准，冲突写入 uncertainty 请人工确认 |
| 预算耗尽（>40 请求或时间<1/3） | 见第 3 节预算兜底，partial 交付 |

异常与不确定性一律写入 `/app/work/exceptions.json`、`uncertainty.json`
（`[{item, reason, severity}]`）。

## 5. 与其他版本的关系

本 Skill 覆盖题面「长上下文：登记簿与重复论述防护」方向。同一仓库另有章节规划与
篇幅论证（v1.0.0）、跨章节一致性、术语引用溯源、意见拆解与改稿台账等方向的独立
Skill（见 GITHUB_URL.txt 指向的仓库目录）。本版可复用 v1.0.0 的章节规划产物
（chapter_plan.json）确定 `--target-section`，但两者引擎独立、可单独运行。
