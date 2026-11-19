---
name: results-discussion-evidence-mapping
description: 结果与讨论章节写作的"讨论证据对照"方向技能。当任务要求讨论段每个论断都能对应到本研究数据或具体文献，需要说明与文献的一致/不一致及可能原因，且引用必须真实存在（出自材料参考文献列表）时使用。核心能力：论断-证据矩阵（claim-evidence matrix）模板、引用真实性核验脚本（逐条核对正文引用与文献列表）、讨论五语步结构、防止只堆引用不讲关系的句式约束。适用于文献对照、证据分级与引用核查。
---

# 结果与讨论章节写作：讨论证据对照方向

## 1. 用途与适用条件

本 Skill 解决讨论段的三个典型失败：**只堆引用不讲关系**（罗列十篇文献却不说明与本研究的一致或不一致）；**论断无锚**（机制、意义、外推性结论找不到数据或文献支撑）；**引用不实**（编造文献、引用不在材料参考文献列表中的工作、作者-年份与文末列表对不上）。

适用条件：输入材料含论文 PDF（带参考文献列表）或独立参考文献文件，需撰写结果与讨论章节。

核心原则：

1. **每条论断必带锚**：讨论段每个论断句后跟【数据：图x/表x】或【文献：作者, 年份】。
2. **引用必出自列表**：正文引用必须能在材料参考文献列表中逐条匹配；匹配不到就删除或改写。
3. **对照必讲关系**：与文献并陈时必须说明"一致/不一致/部分一致 + 可能原因"，不允许无关系词的并列。
4. **矩阵先行**：写讨论段前先填论断-证据矩阵，正文从矩阵生成，矩阵与正文同步交付供复核。

## 2. 输入与输出

输入：`/input/case.json`（case_id、output_contract）、`/input/task.md`、`/input/` 材料（论文 PDF 或 PDF+参考文献文件）。

输出（写入 `/app/output/`）：`result.json`（output_contract 全字段 + case_id + status + sources + uncertainty + change_log）、`results_and_discussion.md`、`claim_evidence_matrix.md`（矩阵）、`citation_report.json`（引用核验输出）、环境允许时 docx/PDF 预览。

## 3. 工作流程

### 步骤 1：读契约与材料

读 case.json/task.md，记录 output_contract 与语言要求。用 `reference/tool_recipes.md` 抽取论文全文；单独抽取**参考文献列表**到 `/app/work/references.txt`（每条一个编号），再切分出第一作者姓氏与年份，存 `/app/work/reference_keys.json`，格式：

```json
[{"key": "Zhang", "year": "2020", "raw": "Zhang, Y. et al. ..."}, {"key": "Smith", "year": "2019", "raw": "..."}]
```

### 步骤 2：准备数据锚点清单

从结果段素材中列出本研究关键观察（图/表级），存 `/app/work/data_anchors.md`：每条一行，"D1 图1B：高剂量组指标 +73%（p = 0.002）"。讨论段的【数据：…】锚只能引用此清单中的条目。

### 步骤 3：填写论断-证据矩阵

按 `templates/claim_evidence_matrix.md` 填 `/app/output/claim_evidence_matrix.md`，每个论断一行：

| 编号 | 论断（一句话） | 类型（数据/文献/推测） | 证据锚 | 与文献关系（一致/不一致/部分一致/不适用） | 可能原因 |
|-|-|-|-|-|-|

规则：

- 类型为"数据"的论断，锚必须来自 data_anchors.md；
- 类型为"文献"的论断，必须写关系列；
- 机制解释一律标"推测"，并在论断末尾带（推测，尚待验证）；
- 矩阵中任何一行无法给出证据锚，该行论断不得进入正文。

### 步骤 4：撰写结果段与讨论段

结果段常规写作（观察+图锚）。讨论段严格按 `reference/discussion_moves.md` 的五语步展开，且：

- 每个论断句后立即给锚：「……【数据：图2B】」「……【文献：Zhang, 2020】」；
- 文献对照句必须含关系词：与……一致 / 与……相反 / 与……部分一致（数值相近但条件不同）/ 本研究未复现……的结果；
- 关系为"不一致"时，必须给至少一个具体层面的可能原因（样本、方法、测量、统计），不允许"原因尚不明确"一笔带过（确实无从判断时在 uncertainty 说明）；
- 不引用与本论断无关的文献凑数；同一文献多处引用可以，但每次都要讲不同关系。

### 步骤 5：引用核验

```bash
python3 /skills/weekly-skill/scripts/verify_citations.py \
  --text /app/output/results_and_discussion.md \
  --matrix /app/output/claim_evidence_matrix.md \
  --refs /app/work/reference_keys.json \
  --out /app/output/citation_report.json
```

脚本检测（细则见 `reference/citation_rules.md`）：

1. 正文引用（(Author, Year)、Author et al. (Year)、[n] 三种格式）逐条匹配 reference_keys.json，无匹配即 fail（疑似虚构引用）；
2. 讨论段每个论断句是否有锚（【数据：…】/【文献：…】）；
3. 矩阵中类型为"文献"的行，关系列是否填写；
4. 矩阵中类型为"推测"的行，正文是否带"（推测，尚待验证）"标注。

未通过必须修改后重跑至 PASS。

### 步骤 6：交付

result.json（同前规范）、矩阵、核验报告；环境允许时生成 docx/PDF；按 `checklists/final_checklist.md` 自查。

## 4. 异常处理

| 情况 | 处置 |
|-|-|
| 材料无参考文献列表 | 讨论段只做内部数据对照与推测（全部标注），文献语步留空并在 uncertainty 注明"材料未提供参考文献，无法做文献对照"；status 视任务要求定 partial |
| 参考文献列表无法解析（扫描件乱码） | OCR 重试；仍失败则按上一条处理 |
| 正文需引用但格式无法匹配（如编号制 [1] 而列表无编号） | 先补编号映射到 references.txt，再核验 |
| 文献结论细节在材料中不完整（只有题录无全文） | 只引用题录能支持的弱论断（"Zhang 等（2020）研究了同类体系"），不得转述其具体数值与结论；uncertainty 注明 |
| 引用制式由 task.md 规定（如 GB/T 7714 编号制） | 以 task.md 为准，核验脚本仍用于真实性检查，格式检查人工按标准核对 |

## 5. 最小调用示例（示意，非真实案例答案）

输入（示意）：`/input/case.json` 含 `{"case_id":"demo-04","output_contract":["section_md","language"]}`；`/input/paper.pdf` 含正文与 8 条参考文献。

调用：抽取全文与文献列表→建 data_anchors.md（D1–D4）→填矩阵（M1–M6）→写讨论段（每句带锚）→verify_citations.py PASS→交付。

示意输出（节选）：

```json
{
  "case_id": "demo-04",
  "section_md": "……本研究观察到高剂量组指标较对照组升高 73%【数据：图1B】。该幅度大于 Zhang 等（2020）报道的 30%【文献：Zhang, 2020】，差异可能源于本研究采用了更长的处理时间（72 h vs 24 h）……我们推测 X 通路参与其中（推测，尚待验证）。",
  "language": "zh",
  "status": "success",
  "sources": {"matrix": "claim_evidence_matrix.md", "citation_report": "citation_report.json"},
  "uncertainty": [],
  "change_log": ["删除一处无法匹配文献列表的引用（原写 Li, 2021，列表中不存在）"]
}
```

## 6. 资源清单

- `scripts/verify_citations.py`：引用真实性与论断锚点核验脚本（stdlib）。
- `templates/claim_evidence_matrix.md`：论断-证据矩阵模板与填写示例。
- `reference/discussion_moves.md`：讨论五语步结构与关系句式。
- `reference/citation_rules.md`：核验脚本判定细则与引用格式说明。
- `reference/tool_recipes.md`：材料与参考文献抽取命令。
- `checklists/final_checklist.md`：交付前自查清单。
