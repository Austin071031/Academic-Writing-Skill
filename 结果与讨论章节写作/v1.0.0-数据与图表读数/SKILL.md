---
name: results-discussion-data-grounding
description: 结果与讨论章节写作的"数据与图表读数"方向技能。当任务要求依据给定的论文PDF、数据表、统计输出等材料撰写结果与讨论章节，且图表数值、单位、误差棒含义、统计量必须被准确读入正文时使用。核心能力：从材料中建立逐面板数值台账（evidence ledger），正文每个数值可回溯到具体图/表/统计输出，并用脚本自动核验正文数值与台账一致后才交付。适用于材料不足时明确标注缺口，不臆造数据。
---

# 结果与讨论章节写作：数据与图表读数方向

## 1. 用途与适用条件

本 Skill 解决科研写作中最常见的失败点：**正文数值与图表对不上**（读数错误、单位换算错误、误差棒含义混淆、有效数字随意、多面板图编号错位、补充材料编号丢失）。

适用条件：任务输入包含科研材料（论文 PDF、图、表、CSV/XLSX 数据、统计检验输出、图注）之一或多个，要求产出结果与讨论章节（或其中一部分）。不适用于：无任何材料的自由写作（此时应在 result.json 中声明 `status: "partial"` 并说明缺口）。

核心原则（贯穿全流程）：

1. **先建台账，再写正文**：正文中出现的每一个数值必须先在数值台账（evidence ledger）中登记。
2. **不回溯不交付**：`scripts/verify_numbers.py` 核验不通过的正文必须修改后再交付。
3. **读不清就标注**：无法从材料中可靠读出的数值，正文用「[待核实]」标注并写入 uncertainty，绝不猜测。
4. **不新增材料外事实**：正文不得引入材料中不存在的数字、文献或结论。

## 2. 输入与输出

输入（运行时由平台提供，禁止假设内容）：

- `/input/case.json`：案例标识 `case_id`、任务约束、`output_contract`（交付字段清单，必须原样出现在 result.json 中）。
- `/input/task.md`：任务说明（受众、文体、语言、篇幅、格式约束）。
- `/input/` 下其余文件：论文 PDF、图表、数据表、统计输出等，**按实际扩展名识别，不按文件名猜测内容**。

输出（写入 `/app/output/`，工作过程写入 `/app/work/`）：

| 文件 | 说明 |
|-|-|
| `result.json` | 结构化结果，含 case_id、output_contract 全部字段、`status`、`sources`、`uncertainty`、`change_log` |
| `results_and_discussion.md` | 可编辑的结果与讨论章节（Markdown，按 task.md 指定语言与文体） |
| `results_and_discussion.docx` / `.pdf` | 若环境有 pandoc / LaTeX 则生成真实渲染件，否则在 result.json 中说明 |
| `evidence_ledger.json` | 数值台账（逐图/表/面板的数值、单位、统计量、原文出处） |
| `verification_report.json` | 数值核验报告（每个数值的匹配状态） |

## 3. 工作流程

### 步骤 1：读取案例契约（≤ 2 次模型请求内完成）

读取 `/input/case.json` 与 `/input/task.md`，提取：case_id、任务类型、语言（缺省则按 task.md 受众判断，国际期刊用英文，中文任务用中文）、output_contract 字段清单、篇幅与格式约束。将 output_contract 字段名原样记录到 `/app/work/contract_fields.txt`。

同时盘点 `/input/` 全部文件并分类登记到 `/app/work/inventory.md`：PDF / 图片（png,jpg,tiff,eps）/ 数据表（csv,tsv,xlsx）/ 统计输出（txt,json,log）/ 参考文献列表。任何一类缺失都记入 uncertainty（如"未提供统计检验输出，显著性仅能依据正文叙述"）。

### 步骤 2：抽取材料内容（用工具，不靠记忆）

按文件类型执行（命令在 `reference/tool_recipes.md` 中）：

- PDF：`pdftotext -layout input.pdf work/paper.txt` 得全文；用 `pdftoppm -png -r 200` 渲染含图页面为 PNG 供读图。
- 数据表：CSV/TSV 用 Python stdlib `csv` 读取；XLSX 优先 `openpyxl`，缺失则用 `pdftotext` 从 PDF 中抽取表格文本。
- 图片：用模型视觉能力直接读取图像内容（坐标刻度、柱高、误差棒、图例、面板标签），逐项口述记录到工作笔记，不要凭印象写。
- 统计输出：逐行读取，记录检验名、统计量、自由度、精确 p 值、效应量、样本量。

**禁止**仅凭领域常识补造数值；**禁止**用文件名标签推断数据内容（runtime contract 明确要求）。

### 步骤 3：建立数值台账 evidence_ledger.json

按 `templates/ledger_schema.md` 的结构手工构建（用脚本 `scripts/build_ledger.py` 校验格式）。台账条目字段：

```json
{
  "id": "F2b-mean-control",
  "source": "图2B",
  "panel": "2B",
  "quantity": "细胞存活率",
  "value": 87.3,
  "unit": "%",
  "error": {"type": "SD", "value": 4.1},
  "n": 3,
  "stat": {"test": "one-way ANOVA + Tukey", "p": 0.002, "vs": "对照组"},
  "quote": "原文图2B柱高与误差棒读数",
  "confidence": "high"
}
```

台账必须覆盖：正文拟引用的**每一个**数值。`confidence` 取 `high`（表/统计输出中直接读出）或 `medium`（从位图读数，注明读数方式）。`error.type` 必须写清是 SD、SEM 还是 95% CI——这是基础 Agent 最常混淆的点（见 `reference/units_and_errors.md` 的判别规则：图注写 "mean ± SD" 则误差棒为 SD；未注明时查正文方法部分；仍不明则标注 uncertainty，不得默认）。

### 步骤 4：撰写结果段与讨论段

按 `templates/section_templates.md` 组织：

- 结果段按图序（图1→图2…）或按研究问题（ whichever task.md 指定；未指定则按图序），每段遵循「主题句（该图回答什么问题）→ 数值呈现（台账数值+单位+误差类型+样本量）→ 组间比较（统计量）→ 必要的小结」，只陈述观察，不解释原因。
- 讨论段每个论断后紧跟证据锚点（【数据：图2B】或【文献：Author, Year】），机制推测必须写「我们推测……（推测，尚待验证）」。
- 术语首次出现给中英文全称与缩写（如 人工智能（AI））。

### 步骤 5：数值核验回路（本 Skill 的核心增益）

运行：

```bash
python3 /skills/weekly-skill/scripts/verify_numbers.py \
  --ledger /app/work/evidence_ledger.json \
  --text /app/output/results_and_discussion.md \
  --out /app/output/verification_report.json
```

脚本将：抽取正文中全部数值（含 87.3%、8.73×10¹、(87.3 ± 4.1)% 等形式），逐一与台账比对（按四舍五入容差匹配），输出每个数值的状态：`matched` / `unmatched`（台账中不存在，必须删除或改回台账值）/ `ambiguous`。若存在 `unmatched`，**必须**修正正文后重跑，直到报告中 `unmatched` 为空；确需保留的新数值（如简单算术汇总）须先补登台账再重跑。

### 步骤 6：交付

1. 生成 `result.json`：`status` 取 `success`（全部完成）或 `partial`（材料缺口导致）；逐字段填 output_contract；`sources` 给出台账与核验报告路径；`uncertainty` 列出读数不确定项与人工确认项；`change_log` 记录写作中的修正。
2. 用 pandoc（若有）生成 docx：`pandoc results_and_discussion.md -o results_and_discussion.docx`；有 LaTeX 工具链则再渲染 PDF 预览；两者皆无则在 result.json 注明"环境无 Office/LaTeX 渲染器，交付 Markdown 源文件"。
3. 最终自查清单见 `checklists/final_checklist.md`，逐项确认。

## 4. 异常处理

| 情况 | 处置 |
|-|-|
| 无 `/input/case.json` | 搜索 `/input` 全部 json；仍无则 `status:"failed"`，说明缺失 |
| 只有位图图表、无数值表 | 视觉读数并标 `confidence: medium`；正文中误差棒含义必须依据图注，图注未注明则写 uncertainty |
| 单位不统一（如 kcal/mol vs kJ/mol） | 按 `reference/units_and_errors.md` 换算并在台账记 `unit_note`；正文全篇统一 |
| 多面板图（A/B/C） | 台账 panel 字段必须到子面板；正文引用写「图2B」而非「图2」 |
| 补充材料（附录图 S1、表 S2） | 编号原样保留（图S1），不得并入主图编号 |
| 统计输出与正文叙述矛盾 | 以统计输出为准，矛盾写入 change_log 与 uncertainty |
| 模型请求或工具失败 | 保留已完成的中间产物；result.json 如实记录失败步骤，不得伪造完成态 |

## 5. 最小调用示例（示意，非真实案例答案）

输入（示意）：`/input/case.json` 含 `{"case_id":"demo-01","output_contract":["section_md","language","word_count"]}`；`/input/paper.pdf` 为一篇含图1（A：对照组存活率 95.2 ± 2.1%，n=3；B：处理组 61.4 ± 3.8%，n=3；图注注明 mean ± SD）的材料。

调用：Agent 按第 3 节流程执行，台账登记上述两个数值后写结果段，运行 verify_numbers.py 通过，交付 result.json。

示意输出（节选，须在实际运行中重新生成）：

```json
{
  "case_id": "demo-01",
  "section_md": "如图1所示，……对照组存活率为 (95.2 ± 2.1)%（n = 3，图1A）；处理组降至 (61.4 ± 3.8)%（n = 3，图1B）……",
  "language": "zh",
  "word_count": 1200,
  "status": "success",
  "sources": {"ledger": "evidence_ledger.json", "verification": "verification_report.json"},
  "uncertainty": [],
  "change_log": ["初稿将误差棒误写为 SEM，依据图注改为 SD"]
}
```

## 6. 资源清单

- `scripts/build_ledger.py`：台账格式校验器（Python 3 stdlib，无依赖）。
- `scripts/verify_numbers.py`：正文数值-台账一致性核验器（stdlib）。
- `templates/ledger_schema.md`：台账字段规范与填写示例。
- `templates/section_templates.md`：结果段/讨论段写作模板。
- `reference/units_and_errors.md`：单位换算、有效数字、SD/SEM/CI 判别、面板编号规则。
- `reference/tool_recipes.md`：PDF/表格/图像/统计输出的抽取命令清单。
- `checklists/final_checklist.md`：交付前自查清单。
