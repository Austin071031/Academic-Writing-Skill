---
name: academic-polish-dualchannel
description: 学术语言润色 Skill（双通道架构：确定性脚本做机械审校，Agent 做逐句编辑决策）。当任务要求对学术文本润色、改写、校对、语法修正、术语统一、缩写规范、语气调整、中英表达质量提升，并要交付改后全文与逐句修改说明时使用。触发示例："润色这段摘要并给出修改说明""统一全文术语和缩写""把这段中译英改成期刊风格"。不触发：纯内容问答、事实查证、计算、整篇翻译——这些直接回答，不得改写原文。流水线交付 polished_full.md、逐句 change_log、术语表、原文—改文对照、审校报告与含 case_id/output_contract 的 result.json，所有产物在 /app/output。
---

# academic-polish-dualchannel：双通道学术语言精修（v1.1.0）

通道一（Agent）：逐句做 keep/modify 决策，每句留痕（原文/改文/类型/理由）。
通道二（确定性脚本）：术语一致性回扫、事实与限定强度守恒检查、清单质量审计、产物组装与终检闸门。
四条承诺：**改得对**（硬错误真消除）、**说得像**（贴合目标文体）、**没改坏**（限定强度/数据/单位/引用/图表指向守恒）、**讲得清**（每处修改可复核）。

## 何时调用 / 何时不调用

- 调用：任务明确要求润色/改写/校对/语言修改/术语统一/语气调整/缩写规范，或要求交付
  "润色后文本＋修改说明/逐句对照/术语表"。
- 不调用：纯内容问答、文献查证、计算、整篇翻译。判断依据是任务动词。
- 拿不准时先完成阶段1任务解析，把依据写入 `task_profile.json` 的 assumptions。

## 执行流程（预算：≤14 次模型调用/案例，脚本 <30 秒）

`<SKILL>` = Skill 安装目录（评测时 `/skills/weekly-skill`）。**随时中断都有有效交付物。**

### 阶段0 预检（0 次模型调用）

```bash
bash <SKILL>/scripts/run_pipeline.sh /input /app/work /app/output
```

读 `/app/work/brief.json`（case_id、output_contract、材料清单、编码问题、题面约束）
与 `/app/work/source_dump.md`（带稳定 ID 的逐句源文本）。brief.issues 全部转入
result.json 的 uncertainty。

### 阶段1 任务解析（≤1 次）

写 `/app/work/task_profile.json`：language、register（期刊论文/学位论文/基金申请书/
审稿回复/英文摘要；不明→默认期刊论文并注明）、scope（全文或指定章节）、
bilingual_alignment、term_table_source、constraints、assumptions、open_questions。

### 阶段2 术语表（0–1 次）

```bash
python3 <SKILL>/scripts/terminology.py build --segments /app/work/source_segments.json \
    --out /app/work [--provided /input/案例自带术语表.csv]
```

审阅 term_table.csv：合并案例自带表（冲突时案例表优先并记 note），确认候选术语。
**润色全程以此表为唯一术语依据**；润色中新引入的写法（如补英文全称）必须回填表格。

### 阶段3 逐句润色（1 次/块，每块 ≤2500 字）

按 source_dump.md 的 ID 分块，逐句决策并**直接用 bash heredoc 写入**
`/app/work/polish_chunks/chunk_NNN.jsonl`（每句一行 JSON，写完立即
`python3 -c "import json,sys; [json.loads(l) for l in open(sys.argv[1])]" file` 验证可解析）：

```json
{"id":"doc-B3-P1-S2","original":"（照抄源句）","polished":"（改后句）",
 "decision":"modify","types":["grammar"],"reason":"主谓不一致：results 为复数主语"}
```

铁律：
1. **最小编辑**：只改需要改的；正确但平淡的句子不因风格偏好重写；keep 也要写理由
   （"无语病""限定强度恰当"等具体依据）。
2. **不许动清单**：数值、单位、统计量、引用编号与 `\cite` 键、图表/公式/章节指向、
   专有名词拼写、限定词强度、否定范围、条件句与量词。
3. **types 受控词表**：grammar/syntax/collocation/punctuation/spelling/long-sentence/
   terminology/abbreviation/register/redundancy/logic/clarity/hedging/formatting/other。
4. **reason 质量标准**（v1.1.0 新增硬要求）：必须指向具体语言现象（哪个词/哪种结构/
   哪条规则），≥8 字；**禁止**"更通顺""更规范""语言优化"类空理由——log_audit.py 会拦截。
5. 范围内每句必须有记录；存疑句标 keep 且 reason 以"存疑："开头，进入人工确认清单。

### 阶段4 清单审计 + 双审校（0 次调用 + 逐条处置）

```bash
python3 <SKILL>/scripts/log_audit.py --work-dir /app/work
python3 <SKILL>/scripts/assemble.py --work-dir /app/work --output-dir /app/output --bilingual
python3 <SKILL>/scripts/terminology.py check --segments /app/work/polished_segments.json \
    --table /app/work/term_table.csv --out /app/work
python3 <SKILL>/scripts/guard_check.py --source /app/work/source_segments.json \
    --chunks /app/work/polish_chunks --out /app/work
```

每条 critical 必须处置：改正 chunk 行，或在 `/app/work/resolutions.jsonl` 记录
`{"flag_id","kind","action":"fixed|justified","note"}`。处置后重跑直至 critical=0。

### 阶段5 回读校验（1 次）

通读 polished_full.md：语义漂移、漏改硬错误、语气贴合、连接词滥用、上下文衔接。
同段重复运行不得推翻已有决策，只做增量修正。

### 阶段6 组装与终检（0 次调用）

```bash
python3 <SKILL>/scripts/assemble.py --work-dir /app/work --output-dir /app/output --bilingual
python3 <SKILL>/scripts/render_previews.py --output-dir /app/output
python3 <SKILL>/scripts/validate_output.py --work-dir /app/work --output-dir /app/output
```

validate 退出码非 0 不得宣告完成；无法修复的写入 result.json 并保持 status=partial。

### 阶段7 诚实收尾（≤1 次）

确认 result.json：status（由 validate 判定）、assumptions、uncertainty（材料缺口/
编码问题/术语冲突）、manual_review_required（存疑句、未提取材料）、change_records.summary。

## 完成定义（DoD，发布前逐条核对）

- [ ] polished_full.md 存在且覆盖范围内全部内容（非提纲、非建议）
- [ ] change_log.jsonl 每句有记录；modify 句的 reason 具体、非套话
- [ ] log_audit critical=0；terminology check critical=0；guard critical=0 或 resolutions 闭环
- [ ] 覆盖率 100%；output_contract 每键有 delivered 或 null_reason
- [ ] uncertainty / manual_review_required 已更新；validate exit=0

## 产物（/app/output）

polished_full.md（改后全文，可直接粘回）、change_log.md/.jsonl、sentence_alignment.md、
diff.html、terminology_table.md/.csv、review_report.md、polished_full.html、
preview_polished.pdf/png（有 CJK 字体时）、result.json。

## 异常处置

编码混乱按 gb18030/big5 重试，仍乱码则标注"无法可靠读取"进 manual_review_required；
LaTeX 数学与 `\cite/\ref` 受保护不改写；术语冲突按 案例自带表 > 领域惯例 > 频次最高 取舍并记 note；
超长输入按章节分块，预算不足时按 edge_cases.md 兜底顺序保存部分结果；
材料缺失如实标注，不编造内容。详见 references/edge_cases.md。

## 依赖

仅 Python 3.8+ 标准库；PDF 提取依次尝试 pdftotext/PyMuPDF/pypdf；预览 PDF 需要 matplotlib
与 CJK 字体，缺失时降级为 HTML 预览并如实说明。

## 最小调用示例

见 examples/minimal_example.md（示意输出标注为示例，非正式案例结果）。
