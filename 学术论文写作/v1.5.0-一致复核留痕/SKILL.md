---
name: consistency-audit-changelog
description: 事实一致性复核与改稿留痕专精的学术写作 Skill。当任务要求成稿前一致性检查、校对修订底稿、或交付可逐条复核的修改记录时使用，例如"校对这篇稿子与数据图表是否一致""按意见改稿并给我修改清单""检查摘要与结果有没有矛盾"。本 Skill 先任务分型（生成/改稿/校对）并快照底稿，写作执行"改动必留痕"红线，成稿后机读三向审计：摘要↔正文数字一致、图表引用↔图注闭环、方法宣布↔结果报告闭环，另查缩写首用定义与待确认闭环；改稿任务自动生成底稿↔终稿逐段 diff（删除/改写/新增逐段列出让作者确认），change_log 为空即警告。输出 /app/output 的 result.json（含 output_contract 全部字段）、manuscript.md/docx、PDF/PNG 预览、audit_report.md、diff_review.md、change_log.md。适用于校对、改稿、成稿前复核任务。
---

# 事实一致性复核与改稿留痕 Skill（改得动专精）

核心原则：**先快照后动笔、三向一致、改动必留痕、复核点明示**。

## 适用与不适用
- 适用：底稿校对/修订/润色、成稿前一致性复核、需要逐条修改记录的协作写作。
- 不适用：无一致对象的全新写作（generate 任务时 diff 引擎自动关闭，仅保留三向审计）。

## 输入与输出
- 输入：`/input/case.json`、`/input/task.md`、底稿与数据/图表/文献材料。
- 输出（`/app/output/`）：`result.json`（含 output_contract 全部字段+case_id）、`manuscript.md`（+docx/pdf/preview）、
  `audit_report.md`（三向审计）、`diff_review.md`（底稿↔终稿逐段 diff，改稿任务）、`change_log.md`（修改记录）、
  `engine_report.json`、`run_log.md`。
- 中间产物：`/app/work/draft_snapshot.json`（底稿逐段快照）、task_profile.md（任务分型）。

## 执行流程（严格按序，写稿优先）

### 0. 预处理（一条命令）
```bash
bash /skills/weekly-skill/scripts/run.sh pre
cat /app/work/brief.json /app/work/task_profile.md
```
得到 brief、任务分型（generate/rewrite/proofread）、底稿快照与术语基线。此时 result.json 已有保底骨架。
**改稿/校对任务未识别到底稿文件时**：在 uncertainty 说明并请人工确认，不得把参考材料当底稿乱改。

### 1. 写稿/改稿（预算主要部分）
写 `/app/work/sections/NN-*.md`，`cat` 合并为 manuscript.md；**同步逐条写 change_log.md**（详见 references/audit_checklist.md）：
1. **改动必留痕**：`- [改写] P003 原句 → 新句 — 依据：M02#l14 数据`；删除、移动、格式调整同样记录。
2. **数字与结论不擅自改**：底稿数值与材料冲突时，以材料为准改并记 change_log；底稿数值材料中查不到的，
   保留并标【待确认：底稿数值未见于本次材料】，不得悄悄删除。
3. **三向一致**：摘要每个数字必须在正文出现；正文每个图/表引用必须有注；方法宣布的每项分析结果节必须有报告。
4. **术语一致**：同一概念全篇同一术语；缩写首用给全称（与材料术语基线对齐）。
5. 校对任务：产物=修订稿+勘误表（audit_report 即证据），勘误逐条含"位置/底稿表述/材料依据/处置"。

### 2. 核验与收尾（一条命令）
```bash
bash /skills/weekly-skill/scripts/run.sh post
cat /app/output/audit_report.md /app/output/diff_review.md /app/output/validation.md
```
机读审计：摘要数字逃逸（FAIL）、图表注缺失（FAIL）、方法结果闭环、缩写、待确认、change_log 空警告。
改稿任务读 diff_review.md 逐段确认删除/新增是否故意。FAIL 返修后重跑 post。

## 异常处理
| 情况 | 处置 |
|-|-|
| 改稿任务无底稿 | uncertainty 说明并按 generate 处理，不虚构 diff |
| 底稿大改（>50% 段落变动） | diff_review 全量列出；change_log 可按节汇总但必须覆盖每处事实改动 |
| 材料与底稿结论冲突 | 以材料为准；底稿结论改写+标注+change_log，不隐瞒冲突 |
| 图片材料 | 图中数值不估读；标【待确认：需人工核对原图】 |
| pandoc/libreoffice 缺失 | 只交付 md，预览标 unavailable |

## 预算纪律
pre/post 纯脚本各 <2 分钟；change_log 随改随记（不是成稿后补写）；diff 由脚本生成，不占写作预算。

依赖：python3≥3.9（纯标准库）；pdftotext/pandoc/LibreOffice/pdftoppm 可选降级。
