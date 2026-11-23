---
name: academic-polish-registerfit
description: 学术语言润色 Skill（文体指纹驱动：先测源稿语域画像，再按目标文体指纹逐句换装，最后用同一组指标验证达标）。当任务要求把学术文本润色为特定期刊/学位论文/基金申请书/审稿回复/英文摘要风格，或要求"按目标期刊风格整体改写""统一全篇语气"时使用。触发示例："把这段摘要改成期刊风格""这份基金本子英译后语气不像，帮我统一"。不触发：纯内容问答、事实查证、计算、整篇翻译——直接回答，不得擅自改写原文。核心机制：style_metrics.py 度量句长/限定词密度/被动/连接词/人称/口语与宣传词，润色前后同一尺量两遍，达标报告随稿交付。产物：/app/output 下 polished 全文、逐句修改卡、术语表、文体指纹对比报告与含 case_id/output_contract 的 result.json。
---

# academic-polish-registerfit：文体指纹驱动的学术润色（v1.4.0）

核心假设：润色"像不像"是可度量的。本 Skill 用一组可计算指标（句长分布、限定词
密度与档位、被动语态、连接词密度、人称、口语词、宣传词）刻画文体指纹：
先测源稿，再定目标画像，逐句换装，最后用**同一把尺**验证达标并随稿交付报告。
事实守恒（数值/引用/限定强度）与语义忠实是硬约束，语域贴合是目标函数。

## 何时调用 / 何时不调用

- 调用：任务要求润色/改写/统一语气/按某文体（期刊、学位论文、基金、审稿回复、
  英文摘要）换装，或要求交付"改后文本＋修改说明"。
- 不调用：纯问答、查证、计算、整篇翻译——直接回答，不改写用户文本。

## 执行流程（预算：≤16 次模型调用/案例）

`<SKILL>` = Skill 安装目录（评测时 `/skills/weekly-skill`）。

### 阶段0 预检（0 次模型调用）

```bash
python3 <SKILL>/scripts/segment_util.py --input-dir /input --work-dir /app/work --output-dir /app/output
```

读 `/app/work/brief.json` 与 `source_dump.md`（带稳定 ID 的逐句源文本）。
brief.issues 转入 result.json uncertainty。

### 阶段1 定目标画像（≤1 次 + 脚本）

- 从 task.md 与案例材料确定目标文体（期刊论文/学位论文/基金申请书/审稿回复/英文摘要；
  不明→默认期刊论文并注明）；若案例自带风格指南，以其条目为准并在
  `/app/work/target_profile.json` 生成后人工补记 custom_rules 字段。

```bash
python3 <SKILL>/scripts/style_metrics.py profile --segments /app/work/source_segments.json \
    --register "期刊论文" --out /app/work
```

### 阶段2 术语表（0–1 次）

```bash
python3 <SKILL>/scripts/terminology.py build --segments /app/work/source_segments.json --out /app/work
```

审阅 term_table.csv；案例自带术语表优先，冲突记 note。

### 阶段3 逐句换装（1 次/块，块 ≤2500 字）

对每句决策 keep/modify，写 `/app/work/polish_chunks/chunk_NNN.jsonl`（每句一行）：

```json
{"id":"doc-B3-P1-S2","original":"...","polished":"...","decision":"modify",
 "types":["register"],"reason":"指向具体语言现象（≥8字）","style_target":"口语化→书面语"}
```

换装铁律：
1. **先守恒后风格**：数值/单位/统计量/引用编号/图表指向/限定强度/否定范围/因果性质
   一个字不动；风格只改词形、句式、连接与人称，不改命题。
2. **最小编辑**：已符合目标画像的句子 keep；只把不达标的句子拉进画像。
3. types 受控词表：grammar/syntax/collocation/punctuation/spelling/long-sentence/
   terminology/abbreviation/register/redundancy/logic/clarity/hedging/formatting/other；
   语域换装记 `register`，顺带修硬错误另记对应类型。
4. reason 指向具体语言现象，禁止"更通顺"类空话；存疑句 keep 且以"存疑："开头。

### 阶段4 指纹验证（0 次调用）

```bash
python3 <SKILL>/scripts/assemble.py --work-dir /app/work --output-dir /app/output --bilingual
python3 <SKILL>/scripts/style_metrics.py compare --source /app/work/source_segments.json \
    --polished /app/work/polished_segments.json --out /app/work
```

`style_report.md` 逐项列出润色前后与目标区间。**每个未达标项必须处置**：
定位到具体句子修正，或在 `/app/work/resolutions.jsonl` 记录理由
（如"长句为定义句不可切"），再重跑 compare。同时跑术语回扫：

```bash
python3 <SKILL>/scripts/terminology.py check --segments /app/work/polished_segments.json \
    --table /app/work/term_table.csv --out /app/work
```

### 阶段5 回读 + 组装终检（≤1 次）

回读 polished_full.md 检查语义漂移与上下文衔接；然后：

```bash
python3 <SKILL>/scripts/assemble.py --work-dir /app/work --output-dir /app/output --bilingual
python3 <SKILL>/scripts/render_previews.py --output-dir /app/output
python3 <SKILL>/scripts/validate_output.py --work-dir /app/work --output-dir /app/output
```

validate 非零退出不得宣告完成；style_report 未达标且未处置的项写入
result.json 的 uncertainty。

### 阶段6 诚实收尾（≤1 次）

result.json 确认 status/assumptions/uncertainty/manual_review_required；
style conformance 摘要写入 artifacts.style_report 与 change_records。

## 产物（/app/output）

polished_full.md、change_log.md/.jsonl、sentence_alignment.md、terminology_table.md/.csv、
**style_report.md**（文体指纹对比，本方向核心产物）、review_report.md、diff.html、
preview 预览、result.json。

## 异常处置

编码混乱按 gb18030/big5 重试；LaTeX 数学与 `\cite/\ref` 保护不改写；目标文体不明
默认期刊论文并在 assumptions 注明；文体内部冲突（题面要求与风格指南冲突）按题面
优先并记 uncertainty；超长按章节分块，预算不足按已闭环块保存 partial；重复运行
以 chunks 为准增量修正。

## 依赖

仅 Python 3.8+ 标准库；PDF 提取依次尝试 pdftotext/PyMuPDF/pypdf。
