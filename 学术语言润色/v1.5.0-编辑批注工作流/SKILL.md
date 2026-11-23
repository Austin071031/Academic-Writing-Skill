---
name: academic-polish-editcards
description: 学术语言润色 Skill（编辑批注工作流：诊断→处方双段制，置信度分级，批注式手稿+编辑卡+作者验收清单）。当任务要求润色、改写、校对、语法修正、术语统一、语气调整，并要求修改留痕可复核、可疑处明确标注时使用。触发示例："润色这段摘要并把不确定的地方标出来""改这段话，我要能逐条接受或拒绝你的修改"。不触发：纯内容问答、事实查证、计算、整篇翻译——直接回答，不得擅自改写原文。核心机制：先诊断后处方，每条编辑一张卡（诊断/处方/理由/置信度），置信度低的一律不擅自改而开人工确认卡；采纳版全文与批注版手稿双交付。产物：/app/output 下 annotated_manuscript.md、polished_full.md、edit_cards、acceptance_checklist 与含 case_id/output_contract 的 result.json。
---

# academic-polish-editcards：编辑批注工作流（v1.5.0）

核心假设：润色的终点不是"改完"，而是**作者能逐条裁决**。本 Skill 模拟专业编辑的
工作方式：先诊断后处方，拿不准的不改；每条编辑一张卡，附上诊断、处方、理由与
置信度；交付批注式手稿（可逐条接受/拒绝）与采纳版全文。
四条承诺：改得对、说得像、没改坏、讲得清（每张卡即证据）。

## 何时调用 / 何时不调用

- 调用：任务动词为 润色/改写/校对/修改/统一术语/调整语气，或要求修改留痕、
  可疑处标注、逐条可接受/拒绝。
- 不调用：纯问答、查证、计算、整篇翻译——直接回答，不改写用户文本。

## 执行流程（预算：≤14 次模型调用/案例）

`<SKILL>` = Skill 安装目录（评测时 `/skills/weekly-skill`）。

### 阶段0 预检（0 次模型调用）

```bash
python3 <SKILL>/scripts/segment_util.py --input-dir /input --work-dir /app/work --output-dir /app/output
```

读 `/app/work/brief.json` 与 `source_dump.md`（带稳定 ID 的逐句源文本）。
brief.issues 转入 result.json uncertainty。

### 阶段1 任务画像（≤1 次）

语言、文体（期刊论文/学位论文/基金/审稿回复/英文摘要；不明→默认期刊论文并注明）、
范围、双语要求、案例自带术语表（有则为准）。写入 `/app/work/task_profile.json`。

### 阶段2 诊断（1 次/块，块 ≤2500 字）

对每句**只诊断不开刀**：问题是什么、证据在哪、属于哪类。写入
`/app/work/edit_records/chunk_NNN.jsonl`（每句一行，action 暂留 keep）：

```json
{"id":"doc-B3-P1-S2","original":"...","action":"keep",
 "diagnosis":"主谓不一致：results 为复数主语而谓语用 shows","types":["grammar"]}
```

无问题的句子 diagnosis 写"未见问题"。**这一阶段禁止改写**——先看清再动刀，
防止顺手改坏。

### 阶段3 处方与分级（与阶段2同块连续完成）

对诊断出问题的句子追加处方字段并定 action：

```json
{"id":"doc-B3-P1-S2","original":"...","action":"apply",
 "diagnosis":"主谓不一致：results 为复数主语而谓语用 shows",
 "prescription":"The experimental results show an improvement.",
 "reason":"主谓一致（results→show）；冠词 an；of 短语缩合","types":["grammar","collocation"],
 "confidence":"high","note":""}
```

分级规则（必须遵守）：
- `confidence=high` 且修改不涉及禁动清单 → `action=apply`。
- 涉及限定强度升降、术语取舍、语义重述、证据强度判断、题面未明确的取舍 →
  `confidence=low`、`action=confirm`，**处方照写但不生效**，开人工确认卡。
- 无问题 → `action=keep` 并写保留依据。

禁动清单（apply 也不得碰）：数值、单位、统计量、引用编号与 `\cite` 键、图表/公式/
章节指向、专有名词拼写、限定词强度、否定范围、量词、因果/相关性质。
types 受控词表：grammar/syntax/collocation/punctuation/spelling/long-sentence/
terminology/abbreviation/register/redundancy/logic/clarity/hedging/formatting/other。
reason 指向具体语言现象（≥8 字），禁止"更通顺"类空话。

### 阶段4 组装批注产物（0 次调用）

```bash
python3 <SKILL>/scripts/annotate.py --work-dir /app/work --output-dir /app/output
```

产出：annotated_manuscript.md（`[E#]~~原文~~ → **改文**[/E#]` 批注标记）、
polished_full.md（apply 生效版）、edit_cards.md/.jsonl、acceptance_checklist.md
（confirm 卡逐条待裁决）、change_log、diff.html、result.json。

### 阶段5 审校与回读（0 次调用 + 1 次）

```bash
python3 <SKILL>/scripts/terminology.py build --segments /app/work/source_segments.json --out /app/work
# Agent 审阅 term_table.csv 后回扫：
python3 <SKILL>/scripts/terminology.py check --segments /app/work/polished_segments.json --table /app/work/term_table.csv --out /app/work
python3 <SKILL>/scripts/validate_output.py --work-dir /app/work --output-dir /app/output
```

回读 polished_full.md 检查语义漂移与衔接；validate 非零退出不得宣告完成。
confirm 卡内容必须原样进入 result.json 的 manual_review_required。

### 阶段6 诚实收尾（≤1 次）

result.json 确认 status/assumptions/uncertainty；change_records.summary 记
applied/confirm/kept 计数。

## 产物（/app/output）

annotated_manuscript.md（批注版，逐条可裁决）、polished_full.md（采纳版）、
edit_cards.md/.jsonl（诊断→处方→理由→置信度）、acceptance_checklist.md
（待裁决项+通用验收勾选）、change_log.md/.jsonl、diff.html、terminology_table、
review_report.md、result.json。

## 异常处置

编码混乱按 gb18030/big5 重试；LaTeX 数学与 `\cite/\ref` 保护不改写；材料缺失/
提取失败如实标注 status 与 uncertainty；超长按章节分块，预算不足按已闭环块保存
partial；重复运行以 edit_records 为准增量修正；题面与风格指南冲突按题面优先并记
uncertainty；中英日混排按句语言处理。

## 依赖

仅 Python 3.8+ 标准库；PDF 提取依次尝试 pdftotext/PyMuPDF/pypdf。
