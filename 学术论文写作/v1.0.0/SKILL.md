---
name: academic-writing-evidence-first
description: 证据优先的学术论文写作与改稿 Skill。当任务给出科研材料（论文 PDF、实验记录、数据 CSV/表格、图表、参考文献列表、访谈/问卷记录等）并要求完成学术写作类产物时使用，例如"根据这些材料写结果节/完整章节稿""把底稿改写成期刊格式""校对稿件与数据是否一致""整理参考文献并核对引用""生成中英双语摘要""按模板补齐章节与声明字段"。本 Skill 先建材料索引与事实底稿（数值、单位、样本量、文献条目全部带锚点溯源），再分章写作，成稿前用机读一致性检查核验每个数字、每条引用、每个必备章节，缺失与冲突显式标注【待确认】，全程留痕。输出 /app/output 下的 result.json（含 case.json output_contract 全部字段与 case_id）、可编辑 manuscript.md/docx、PDF/PNG 预览、证据映射表、一致性报告与修改记录。仅适用于"有给定材料、有明确体裁与格式约束"的写作任务；不适用于无材料的自由选题写作（此时说明并退出）。
---

# 证据优先学术写作 Skill

核心原则：**先溯源，后写作；先机读核验，后交付**。稿件中的每个数字、每条引用、每个关键论断都必须能指回具体材料位置或具体文献条目；材料没有的内容不补全，显式标注。

## 用途与适用条件
把 `/input` 的科研材料与任务约束转化为**结构完整、事实可逐条回溯、可直接继续编辑**的学术写作产物。
支持六类任务（可组合）：**生成**（按材料写章节稿/摘要/全稿）、**改写**（换受众/换体裁/压缩扩写）、
**校对**（正文与数据、图表、文献的一致性核查与修订）、**结构化**（材料整理为可引用索引与章节框架）、
**双语**（中英互译并保持数值与引用一致）、**引用管理**（建库、统一格式、核对引用对应）。
适用：有源材料（PDF/CSV/TXT/MD/DOCX/图片）、任务说明（task.md）与约束（体裁/受众/字数/引用格式）明确的场景，中英文均可。
不适用：无材料凭空选题写作（此时在 result.json 中说明 blocked 原因并以 partial 退出）。

## 输入与输出
- 输入：`/input/case.json`（`case_id`、`output_contract`、约束字段）、`/input/task.md`（任务说明）、
  材料文件（PDF/CSV/TSV/TXT/MD/DOCX/JSON/图片，分布在 /input 任意子目录）。
- 输出（`/app/output/`，字段定义见 `references/output_schema.md`）：
  `result.json`（**必须含 output_contract 全部字段 + case_id**，含 status/sources/uncertainty/change_log）、
  `manuscript.md`（终稿，章节层级与图注编号完整）、`manuscript.docx`（可编辑版）、
  `manuscript.pdf` 与 `preview/page-*.png`（渲染预览）、
  `evidence_map.md/.json`（论断/数字/引用 → 材料锚点逐条映射）、
  `consistency_report.md/.json`（机读核验结果）、`change_log.md`（改写留痕）、`run_log.md`。
- 中间产物（brief、材料索引、事实底稿、文献库、分章草稿）放 `/app/work/` 供复核。

## 资源清单（安装后为 /skills/weekly-skill）
| 路径 | 作用 |
|-|-|
| `scripts/inspect_case.py` | 预检：解析 case.json/task.md → brief.json（任务类型、必备章节、字数、引用格式、语言、材料清单）；**立即写 result.json 保底骨架** |
| `scripts/build_material_index.py` | 材料索引：PDF/ DOCX/CSV/TXT/MD 提取带锚点（页号/行号/表名）的文本段 → material_index.json + 限长 materials_digest.md |
| `scripts/extract_facts.py` | 事实底稿：CSV 列统计与原始数值、文本中含数值/单位的句子 → facts.json；参考文献行解析 → bibliography.json，全部带溯源 |
| `scripts/check_consistency.py` | 机读核验：稿件每个数字能否在材料中找到、每个引用键是否存在于文献库且被使用、必备章节是否齐全、占位符清单 → consistency_report |
| `scripts/render_preview.py` | manuscript.md → docx（pandoc/python-docx 回退）→ PDF（LibreOffice 回退）→ PNG 预览，逐步降级如实记录 |
| `scripts/assemble_result.py` | 按 case.json output_contract 逐字段组装 result.json：已知语义字段映射真实产物，占位符与 FAIL 项自动进 uncertainty，status 与一致性 verdict 联动 |
| `scripts/validate_output.py` | 交付前终检：result.json 契约字段齐全、声明的产物文件真实存在、状态与证据一致 |
| `scripts/run_pipeline.sh` | 韧性流水线：`pre`（预检+索引+事实，全自动）与 `post`（核验+渲染+终检）两段，每段落盘 checkpoint，失败立即保底 partial |
| `references/output_schema.md` | result.json 字段与 /app/output 布局约定 |
| `references/fact_fidelity.md` | 写作红线：数值/单位/统计量转写规则、趋势≠因果、缺失标注规范 |
| `references/citation_rules.md` | 引用规则：论断—引用绑定、格式统一（GB/T 7714/APA/IEEE/数字顺序）、装饰性引用识别 |
| `references/section_templates.md` | 各体裁章节模板（IMRaD 全稿/结果节/摘要/双语摘要/审稿回复/结构化成稿）与详略规则 |
| `references/consistency_checklist.md` | 一致性检查覆盖项与人工复核点清单 |
| `references/worked_example.md` | 合成最小示例（输入→调用→示意输出，已标明为示例，非正式案例） |

依赖：python3 ≥ 3.9（全部脚本仅用标准库）；pdftotext/pdftoppm（PDF 提取与预览，缺失时降级）；
pandoc 或 python-docx（docx 生成，缺失时只交付 md 并注明）；LibreOffice（PDF 预览，缺失时跳过并注明）。详见 README.md。

## 执行流程（严格按序；每步追加 /app/output/run_log.md）

### 0. 预检 + 自动材料处理（一段命令完成）
```bash
bash /skills/weekly-skill/scripts/run_pipeline.sh pre --input /input --work /app/work --out /app/output
cat /app/work/brief.json
```
得到：brief.json（task_modes、required_sections、word_target、citation_style、language、材料清单、ISSUE 列表）、
material_index.json、materials_digest.md（限长摘要，优先读它而非逐个打开原材料）、facts.json、bibliography.json。
**此时 /app/output/result.json 已有 partial 保底骨架**——后续任何一步超时或失败都不会空手。
ISSUE（缺 task.md、材料为空、约束冲突等）逐条处理或写入 uncertainty。

### 1. 读材料、定证据策略
- 读 `materials_digest.md` 与 `facts.json`、`bibliography.json`；需要某段原文时再按锚点打开对应材料文件核对。
- 确定章节方案：按 `brief.required_sections` 与 `references/section_templates.md` 中对应体裁模板列章节目录，
  写入 `/app/work/outline.json`（每节：标题、要点、引用的 facts/材料锚点/文献键、预计字数）。
- 任务为改写/校对时：先读底稿原文，把"原文句 → 改动类型 → 依据"列入 change_log 计划，再动笔。

### 2. 分章写作（遵守 `references/fact_fidelity.md` 全部红线）
逐节写 `/app/work/sections/<NN>-<slug>.md`，每节一次完成、立即落盘：
- **数字只从 facts.json 与材料锚点取**：写入稿件的每个数值、单位、样本量、误差范围、显著性标记，
  必须能在 facts.json 或材料文本中找到原文；找不到的不得写入，改用【待确认：缺XX数据】。
- **引用只从 bibliography.json 取**：按 brief.citation_style 统一格式；每条引用必须支撑它所在的那句论断
  （规则见 `references/citation_rules.md`）；材料外文献一律不得新增，除非 task.md 明确允许且真实可查（标 external）。
- **趋势≠因果**：材料未做因果/统计检验时，用"提示/相关/观察到"，禁用"导致/证明/显著提升"。
- **缺失显式标注**：缺图注、缺声明字段、材料冲突，就地【待确认：…】并同步记入 uncertainty 计划。
- 同步维护 `/app/work/evidence_map.json`：每个关键论断/数字/图注 → `{claim, source: material_id#locator 或 ref_key, type}`。
- 图注：编号连续（图 1、图 2…），内容只描述材料中图面与数据真实呈现的信息。

### 3. 合并与机读核验（一致性不过关必须返修）
```bash
cat /app/work/sections/*.md > /app/output/manuscript.md   # 按 outline 顺序
python3 /skills/weekly-skill/scripts/check_consistency.py --manuscript /app/output/manuscript.md --work /app/work --out /app/output
```
读 consistency_report：**凡 FAIL 项（数字无出处、引用悬空、缺必备章节）必须返修后重跑**；
WARN 项（文献缺 DOI、未被引用的条目、占位符）逐条确认，保留的写入 uncertainty。
校对类任务：报告本身即主要产物，改写处同步记入 change_log.md。

### 4. 渲染、组装、终检（一段命令完成）
```bash
bash /skills/weekly-skill/scripts/run_pipeline.sh post --input /input --work /app/work --out /app/output
```
自动完成：evidence_map/change_log 落盘 → manuscript.docx + manuscript.pdf + preview/page-*.png 渲染（逐级降级）→
按 case.json output_contract 逐字段组装 result.json（先照抄全部字段名，逐字段填实际产物路径/内容，无法完成的字段填
`unavailable` + 原因）→ validate_output 终检。
终检 FAIL 时修复后重跑 `post`；无法修复则如实置 status=partial 并在 result.json 写明失败点与人工接管位置。

### 预算纪律（64 次模型请求 / 900 秒）
- pre/post 两段为纯脚本（各约 1–2 分钟），不要逐文件手工提取材料，信任索引与事实底稿。
- 写作按节推进、每节落盘；长稿优先保证必备章节齐全且核验通过，再补次要章节。
- 每完成一个阶段就更新 result.json；剩余预算不足时先保证"核验通过的 partial"而非"未核验的全稿"。

## 异常处理
| 情况 | 处置 |
|-|-|
| 缺 case.json / task.md / 材料目录为空 | 缺失清单写入 result.json，status=partial（材料全缺则 failed），说明人工接管位置 |
| 材料格式不认识 / PDF 提取失败 / 文献取不到全文 | 该材料标 `unreadable`，相关论断不得写入，列入 uncertainty；图片材料注明需人工看图 |
| 材料超长超上下文 | 只读 materials_digest.md 与 facts.json；需要细节时按锚点精确打开，不全文读入 |
| 数字在稿件与材料间冲突 | 以材料原文为准改稿件；两处材料互相冲突时保留材料口径并【待确认：冲突】 |
| 引用格式不认识 | 退化为 GB/T 7714 顺序编码制并在 change_log 说明 |
| 字数约束冲突（材料不足以支撑目标字数） | 写满事实内容为止，不注水；在 uncertainty 说明实际字数与原因 |
| pandoc / LibreOffice 缺失 | 只交付 manuscript.md，docx/pdf 字段标 unavailable + 原因，不为交付物造假 |
| 重复运行 | 脚本幂等；sections/ 下已有草稿时先读再续写，不覆盖不重来 |
