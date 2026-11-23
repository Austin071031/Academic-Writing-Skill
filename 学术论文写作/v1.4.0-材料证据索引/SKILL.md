---
name: material-evidence-indexing
description: 研究材料组织与证据索引专精的学术写作 Skill。当任务给出分散的实验记录、数据文件、访谈/问卷、代码输出、补充材料并要求整理成可引用索引、或基于多源材料写作时使用，例如"把这些材料整理成证据索引""多份实验记录口径不一致，据此写稿""核对材料冗余与冲突"。本 Skill 先把全部材料转为带行号锚点的索引与限长摘要，并做三登记：冗余（跨材料近重复）、冲突（同参数不同值）、缺失（不可读/无支撑）；写作执行"关键论断挂锚点"红线并产出证据映射表；成稿后机读三闭环：冲突必须在稿件标注或留痕裁决、每份材料必须使用或说明弃用、数字必须命中材料语料。输出 /app/output 的 result.json（含 output_contract 全部字段）、manuscript.md/docx、PDF/PNG 预览、material_audit.md、evidence_map.md。适用于多源异构材料的整理与写作任务。
---

# 材料组织与证据索引 Skill（研究材料组织专精）

核心原则：**索引先行、三登记（冗余/冲突/缺失）、论断挂锚点、闭环才交付**。

## 适用与不适用
- 适用：分散多源材料（记录/数据/问卷/补充材料/原文 PDF）的整理、冲突裁决、基于材料索引的写作。
- 不适用：单一底稿的纯润色（材料索引价值低时引擎自动降级为数字溯源检查）。

## 输入与输出
- 输入：`/input/case.json`、`/input/task.md`、多源材料。
- 输出（`/app/output/`）：`result.json`（含 output_contract 全部字段+case_id）、`manuscript.md`（+docx/pdf/preview）、
  `material_audit.md`（三闭环报告）、`evidence_map.md`（论断→锚点映射）、`engine_report.json`、`run_log.md`。
- 中间产物：`/app/work/material_index.md`（索引+三登记+限长摘要）、register.json、text/Mxx.txt（全文）。

## 执行流程（严格按序，写稿优先）

### 0. 预处理（一条命令）
```bash
bash /skills/weekly-skill/scripts/run.sh pre
cat /app/work/brief.json /app/work/material_index.md
```
得到 brief 与**材料索引**：材料清单、冲突登记（同参数不同值）、冗余登记、缺失登记、限长摘要。
此时 result.json 已有保底骨架。**先读冲突登记**——写作前决定每个冲突的处置（裁决口径/标【待确认：冲突】）。

### 1. 写稿（预算主要部分）
逐节写 `/app/work/sections/NN-*.md`，`cat` 合并为 manuscript.md；同步写 `/app/output/evidence_map.md`。红线（详见 references/material_rules.md）：
1. **关键论断挂锚点**：每个关键事实/数字/引用在 evidence_map.md 记一行 `| 论断 | 类型 | 锚点 Mxx#l行号 |`。
2. **冲突处置留痕**：采用某口径 → change_log 记"参数 X 采用 M02 口径（值 v），M05 的 w 弃用，原因…"；
   无法裁决 → 正文标【待确认：冲突 M02(v) vs M05(w)】。
3. **冗余只引一处**：重复材料选信息最全的一份引用，其余在 evidence_map 注"冗余同源"。
4. **材料必须使用或说明**：每份材料要么支撑稿件某部分，要么在 evidence_map 末尾"未使用材料"节说明弃用原因。
5. 数字只用材料中出现的值；缺失标【待确认】；图片材料数值不估读。

### 2. 核验与收尾（一条命令）
```bash
bash /skills/weekly-skill/scripts/run.sh post
cat /app/output/material_audit.md /app/output/validation.md
```
机读三闭环：冲突闭环（稿件标注或 change_log 裁决）、覆盖闭环（材料全使用或说明）、数字溯源。
FAIL 必须返修后重跑 post。

## 异常处理
| 情况 | 处置 |
|-|-|
| 材料超长 | 只读 material_index.md 摘要；需细节按锚点精确打开，不全文读入 |
| 冲突过多（>20） | 只处理与稿件论断相关的冲突，其余列入 uncertainty"待人工裁决" |
| 材料格式不认识 | 标 unreadable 入缺失登记；相关论断不写入 |
| 图片/扫描件 | 不估读数值；引用原图并标【待确认：需人工看图】 |
| pandoc/libreoffice 缺失 | 只交付 md，预览标 unavailable |

## 预算纪律
pre/post 纯脚本各 <2 分钟；evidence_map 随写随记（不是成稿后补）；冲突处置在动笔前定。

依赖：python3≥3.9（纯标准库）；pdftotext/pandoc/LibreOffice/pdftoppm 可选降级。
