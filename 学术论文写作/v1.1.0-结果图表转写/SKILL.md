---
name: results-transcription-data-fidelity
description: 实验结果与图表转写专精的学术写作 Skill。当任务给出实验数据（CSV/表格/实验记录）、图表材料并要求撰写或修改"结果"相关章节、图注表注时使用，例如"根据数据写结果节""核对正文数字与数据是否一致""补写图注"。本 Skill 先把全部数据材料转为带单元格/行号锚点的数值台账（写作的唯一数字来源），再指导写作结果段与图注，成稿后机读核验：稿件每个数字必须命中台账、由材料推出的值必须标注【计算值：算式】、每个图表引用必须有规范图注、趋势不写成因果。输出 /app/output 的 result.json（含 case.json output_contract 全部字段）、manuscript.md/docx、PDF/PNG 预览、number_trace.md 数字溯源报告。仅适用于有数据/图表材料的结果写作与转写任务。
---

# 结果与图表转写 Skill（数据保真专精）

核心原则：**台账先行、数字必溯源、图注成规范、趋势非因果**。

## 适用与不适用
- 适用：有实验数据（CSV/TSV/Excel 转出的表格）、实验记录、论文 PDF、图表材料的"结果"写作、图注补写、数字一致性校对。
- 不适用：无数据材料的纯文献综述写作（材料全缺时按异常处理以 partial 退出并说明）。

## 输入与输出
- 输入：`/input/case.json`（case_id、output_contract、约束）、`/input/task.md`、数据与图表材料。
- 输出（`/app/output/`）：`result.json`（含 output_contract 全部字段+case_id）、`manuscript.md`（+docx/pdf/preview PNG）、
  `number_trace.md`（数字溯源核验报告）、`engine_report.json`（机读 verdict）、`run_log.md`、改稿任务另附 `change_log.md`。
- 中间产物（`/app/work/`）：brief.json、facts_ledger.json/md（数值台账）、sections/ 分节草稿。

## 执行流程（严格按序，写稿优先）

### 0. 预处理（一条命令）
```bash
bash /skills/weekly-skill/scripts/run.sh pre
cat /app/work/brief.json /app/work/facts_ledger.md
```
得到 brief（必备章节/引用格式/字数/材料清单/ISSUE）与**数值台账**（每个数字带 fact_id 与材料锚点）。
此时 /app/output/result.json 已有保底骨架。

### 1. 写稿（预算的主要部分，先完成完整稿件再增强）
按 brief.required_sections 逐节写 `/app/work/sections/NN-*.md`，然后 `cat /app/work/sections/*.md > /app/output/manuscript.md`。
写作红线（详见 references/results_writing.md）：
1. **数字只从台账取**：每个数值/单位/样本量/误差/显著性必须对应某条 fact_id；台账没有的不得写。
2. **推导值须标注**：由材料数字计算得出（差值、百分比变化）写为 `31.1 个百分点【计算值：92.3−61.2】`。
3. **统计口径照抄**：SD/SEM/95%CI 不互换；材料没写检验方法就不得写"显著"。
4. **趋势≠因果**：无因果检验时禁用"导致/证明"，用"提示/相关/观察到"。
5. **图注公式**：`图 N 标题。（样本量 n=…；误差棒为 SD/SEM；统计方法；数据来源材料锚点）`——材料没给的信息标【待确认】。
6. 正文每个"图 N/表 N"引用都必须有对应图/表注；缺材料的图注标【待确认：缺图面信息】。
7. 缺失数据就地标【待确认：…】，不编造。

### 2. 核验与收尾（一条命令）
```bash
bash /skills/weekly-skill/scripts/run.sh post
cat /app/output/number_trace.md /app/output/validation.md
```
engine_check 机读核验：未命中台账的数字清单（**必须返修后重跑 post**）、缺图注清单、因果措辞警告。
verdict=FAIL 时 result.json 自动置 partial；全部 PASS/WARN 才允许 success。

## 异常处理
| 情况 | 处置 |
|-|-|
| 无数据文件（只有 PDF/文本） | 台账退化为文本数值句子；仍可用，run_log 注明 |
| 数据与正文底稿冲突 | 以数据材料为准，冲突处【待确认：M0x 与底稿口径冲突】并记 change_log |
| 图片材料无数值文本 | 不得估读图中数值；引用原图并标【待确认：图中数值需人工核对】 |
| 字数不足 | 写满事实为止，不注水；uncertainty 说明实际字数 |
| pandoc/libreoffice 缺失 | 只交付 md，预览字段标 unavailable（不造假） |

## 预算纪律（64 请求/900 秒）
pre/post 为纯脚本（各<2 分钟）；写作按节落盘，先完整后润色；剩余预算不足时优先保证"核验 PASS 的完整稿"。

依赖：python3≥3.9（脚本纯标准库）；pdftotext/pdftoppm、pandoc、LibreOffice 可选（缺失自动降级并如实记录）。
