---
name: citation-integrity-binding
description: 参考文献与引用核验专精的学术写作 Skill。当任务涉及撰写带引用的章节、整理/统一参考文献格式、核对引用与文献对应关系时使用，例如"写引言并规范引用""核对这篇稿子的参考文献""统一为 GB/T 7714"。本 Skill 先从材料解析文献库（作者/年份/刊名/DOI 带锚点、缺字段不补造），写作时执行"论断—引用绑定"红线（每条引用必须支撑所在句），成稿后机读五检：悬空引用、装饰性未引用条目、编号连续性、格式混用、字段完整性，并生成带上下文的绑定复核表。输出 /app/output 的 result.json（含 output_contract 全部字段）、manuscript.md/docx、PDF/PNG 预览、citation_audit.md。仅适用于有文献材料或任务要求引用规范的写作任务。
---

# 引用核验与论断绑定 Skill（引得对专精）

核心原则：**文献库唯一来源、引用必绑论断、格式全篇统一、缺字段不补造**。

## 适用与不适用
- 适用：引言/相关工作/讨论等带引用章节的写作与改写；参考文献整理、去重、格式统一；引用错配核查。
- 不适用：材料无任何文献条目且任务不要求引用（按通用写作处理时本引擎自动降级为仅格式检查）。

## 输入与输出
- 输入：`/input/case.json`、`/input/task.md`、含参考文献的材料（PDF 原文、refs 列表、.bib 等）。
- 输出（`/app/output/`）：`result.json`（含 output_contract 全部字段+case_id）、`manuscript.md`（+docx/pdf/preview）、
  `citation_audit.md`（五检报告+绑定复核表）、`engine_report.json`、`run_log.md`。
- 中间产物：`/app/work/library.json/md`（文献库）、brief.json、sections/。

## 执行流程（严格按序，写稿优先）

### 0. 预处理（一条命令）
```bash
bash /skills/weekly-skill/scripts/run.sh pre
cat /app/work/brief.json /app/work/library.md
```
得到 brief（引用格式/必备章节/约束）与**文献库**（ref_key、raw 原文、缺字段标记、材料锚点）。
此时 result.json 已有保底骨架。

### 1. 写稿（预算主要部分）
逐节写 `/app/work/sections/NN-*.md`，`cat` 合并为 `/app/output/manuscript.md`。引用红线（详见 references/binding_rules.md）：
1. **只用文献库条目**：引用前核对 ref_key 的 raw（作者/年份/刊名/DOI）；库中无此文献不得引用；
   任务明确允许外部补充时只用真实可查条目（作者/年份/刊名/DOI 齐全），记 change_log 并标 external。
2. **引用必绑论断**：每条引用必须支撑它所在的那句论断——背景断言引综述、数据断言引原始研究、方法断言引方法文献；
   禁止"本节主题相关就挂上"的装饰性引用。
3. **格式统一**：按 brief.citation_style（GB/T 7714 顺序编码 `[1]`/APA `(Smith, 2020)`/IEEE `[1]`，模板见 references/citation_styles.md）；
   全篇不得混用；文献表按正文首次引用顺序编号。
4. **字段照抄**：条目字段照抄 library raw；缺 DOI/卷期页保持缺失（引擎仅 WARN），不得编造。
5. 缺文献支撑的事实断言：删除、改写为不携带事实的过渡句，或标【待确认：无文献支撑】。

### 2. 核验与收尾（一条命令）
```bash
bash /skills/weekly-skill/scripts/run.sh post
cat /app/output/citation_audit.md /app/output/validation.md
```
机读五检：悬空引用、装饰性未引用条目、编号连续性、格式混用、字段完整性（FAIL 必须返修后重跑）。
**然后逐条复核绑定表**：citation_audit.md 中的"论断—引用绑定表"逐条确认引用语义支撑所在句，不支撑的改引用或改句子，改完重跑 post。

## 异常处理
| 情况 | 处置 |
|-|-|
| 材料无文献条目且任务要求引用 | uncertainty 写明"材料未提供文献，无法建立引用"，不虚构 |
| 文献条目解析不全（缺作者/年份） | 保持原样引用并 WARN； uncertainty 列出 |
| 引用格式不认识 | 退化 GB/T 7714 顺序编码制，记 change_log |
| 底稿已有引用编号与文献表错位 | 以文献表为准重排正文编号，逐条记 change_log |
| pandoc/libreoffice 缺失 | 只交付 md，预览标 unavailable |

## 预算纪律
pre/post 纯脚本各 <2 分钟；绑定表语义复核控制在 1–2 次响应；先完整稿后核验。

依赖：python3≥3.9（纯标准库）；pdftotext/pandoc/LibreOffice/pdftoppm 可选，缺失自动降级。
