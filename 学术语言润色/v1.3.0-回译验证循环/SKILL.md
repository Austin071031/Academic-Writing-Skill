---
name: academic-polish-backtranslation
description: 学术语言润色 Skill（回译验证循环驱动：逐句润色→关键句回译→主张矩阵逐格对照→漂移修复）。当任务要求对学术文本润色、改写、校对、术语统一、中英表达质量提升，并要求交付改后全文与逐句修改说明时使用。触发示例："润色这段摘要并给出修改说明""把这段中译英改得像母语者写的，别改我的结论"。不触发：纯内容问答、事实查证、计算、整篇翻译——直接回答，不得擅自改写原文。核心机制：含数值/引用/限定词的句子润色后必须回译，主张矩阵（限定词×数值×单位×引用×图表×因果×否定）逐格对照，不一致即修复或留证。产物：/app/output 下 polished 全文、逐句修改卡、术语表、双语对照、漂移报告与含 case_id/output_contract 的 result.json。
---

# academic-polish-backtranslation：回译验证循环的学术精修（v1.3.0）

核心假设：润色最大的风险不是改不好，而是**改偏了没人发现**。本 Skill 用验证循环
替代一次性修改：每处修改都要经得起"回译过来还是不是那句话"的考验。
四条承诺：改得对、说得像、**没改坏（回译可证）**、讲得清。

## 何时调用 / 何时不调用

- 调用：任务动词为 润色/改写/校对/修改/统一术语/调整语气，或要求交付"改后文本＋修改说明"。
- 不调用：纯内容问答、查证、计算、整篇翻译——直接回答，不改写用户文本。

## 执行流程（预算：≤16 次模型调用/案例）

`<SKILL>` = Skill 安装目录（评测时 `/skills/weekly-skill`）。

### 阶段0 预检（0 次模型调用）

```bash
python3 <SKILL>/scripts/segment_util.py --input-dir /input --work-dir /app/work --output-dir /app/output
```

产出 `/app/work/brief.json`（case_id、output_contract、材料、编码状况）、
`source_segments.json`、`source_dump.md`（带稳定 ID 的逐句源文本）、result.json 骨架。
brief.issues 全部转入 uncertainty。

### 阶段1 任务画像 + 关键句识别（1 次）

- 画像：语言、文体（期刊论文/学位论文/基金/审稿回复/英文摘要；不明→默认期刊论文并注明）、
  范围、双语要求、案例自带术语表（有则为准）。写入 /app/work/task_profile.json。
- 关键句 = 含数值、单位、引用编号、图表指向、限定词、否定词或因果词的句子。
  `segment_util.py` 已在 source_dump.md 中用 `【K】` 标出；以标记为准，不凭感觉。

### 阶段2 逐句润色 + 修改卡（1 次/块，块 ≤2500 字）

对每句决策 keep/modify，写入 `/app/work/polish_chunks/chunk_NNN.jsonl`（每句一行）：

```json
{"id":"doc-B3-P1-S2","original":"...","polished":"...","decision":"modify",
 "types":["grammar"],"reason":"指向具体语言现象（≥8字）","key":true}
```

铁律：最小编辑（正确但平淡的句子 keep）；禁动清单（数值/单位/统计量/引用/图表指向/
限定强度/否定范围/因果性质）；types 受控词表（grammar/syntax/collocation/punctuation/
spelling/long-sentence/terminology/abbreviation/register/redundancy/logic/clarity/
hedging/formatting/other）；reason 禁止"更通顺"类空话；存疑句 keep 且 reason 以"存疑："开头。

### 阶段3 回译验证（本 Skill 的核心，1 次/块）

对**每个 modify 的关键句**做往返校验：
1. **回译**：把 polished 句译回源语言（英改中→译回中文；中改英→译回英文；纯中文稿→
   用另一种规范中文重述；纯英文稿→用另一种英文句式重述）。
2. **主张矩阵对照**：为原文与回译文各填一行矩阵（写入 chunk 行的 `claims` 字段）：

```json
{"claims":{"hedging":"中档（表明）","numbers":"15%","units":"%","citations":"[1]",
           "pointers":"图2","causality":"相关","negation":"无"}}
```

3. **逐格比对**：七格全部一致 → 通过，在 reason 末尾加"回译一致"。
   不一致 → 修正 polished 再回译；最多两轮，仍不一致 → 回退为 keep 并在 reason 写
   "回译漂移，回退保留原文"，句 ID 进 manual_review_required。

非关键句的 modify 不必回译，但仍受禁动清单约束。

### 阶段4 机读校验（0 次调用）

```bash
python3 <SKILL>/scripts/claims_check.py --work-dir /app/work
```

脚本复核：claims 矩阵的 numbers/units/citations/pointers 格与原文机读抽取是否一致、
关键句 modify 是否都有回译通过标记、覆盖率。critical 逐条处置（改正或
/app/work/resolutions.jsonl 记录处置）。

### 阶段5 术语回扫 + 组装（0–1 次）

```bash
python3 <SKILL>/scripts/terminology.py build --segments /app/work/source_segments.json --out /app/work
# Agent 审阅 term_table.csv 后：
python3 <SKILL>/scripts/terminology.py check --segments /app/work/polished_segments.json --table /app/work/term_table.csv --out /app/work
python3 <SKILL>/scripts/assemble.py --work-dir /app/work --output-dir /app/output --bilingual
python3 <SKILL>/scripts/validate_output.py --work-dir /app/work --output-dir /app/output
```

术语冲突按 案例自带表 > 领域惯例 > 频次最高 取舍并记 note；validate 非零退出不得宣告完成。

### 阶段6 诚实收尾（≤1 次）

result.json 确认 status/assumptions/uncertainty/manual_review_required；回退句与两轮
仍未一致的关键句必须出现在 manual_review_required。

## 产物（/app/output）

polished_full.md、change_log.md/.jsonl（含 claims 与回译结论）、sentence_alignment.md、
terminology_table.md/.csv、drift_report.md（回译验证报告：每句通过/修复/回退）、
review_report.md、diff.html、result.json。

## 异常处置

编码混乱按 gb18030/big5 重试，仍乱码标注"无法可靠读取"不猜内容；LaTeX 数学与
`\cite/\ref` 受保护不改写；超长输入按章节分块，预算不足时按"已闭环块优先"保存
partial；重复运行以已有 chunks 为准增量修正，结论不漂移。材料缺失如实标注 status。

## 依赖

仅 Python 3.8+ 标准库；PDF 提取依次尝试 pdftotext/PyMuPDF/pypdf，失败如实标注。
