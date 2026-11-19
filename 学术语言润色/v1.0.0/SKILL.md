---
name: academic-language-polisher
description: 学术语言润色 Skill（术语表驱动 + 限定强度守恒 + 逐句留痕）。当任务要求对学术文本进行润色、改写、校对、语言修改、语法修正、术语统一、缩写规范、语气/语域调整、中英互译后的语言质量提升、期刊/学位论文/基金申请书/审稿回复/英文摘要的文体修改，并要求交付改后全文与修改说明时使用。典型触发：给定稿件（txt/md/tex/docx/pdf）要求“润色这段摘要”“统一全文术语并修改语病”“把这段中译英改成符合期刊风格的英文”“按审稿回复语气改写”。不做的事：纯内容问答、文献事实查证、数值计算、完整翻译任务（非润色）——这些场景不得擅自改写原文，直接回答即可。流水线由确定性脚本（分句、术语表、守恒检查、组装、终检）与 Agent 的逐句润色决策组成，交付 /app/output 下可编辑产物与含 case_id、output_contract 全字段的 result.json。
---

# academic-language-polisher：术语表驱动的学术语言精修

四条工作承诺，每一步都要能回答：**改得对**（硬错误真正消除，不是换一种说法掩盖）、
**说得像**（符合目标文体与语域，术语全篇统一）、**没改坏**（限定强度、数据、单位、
引用编号、图表指向原样保留）、**讲得清**（每处修改有原文、改文、类型、理由，第三方能判断该不该改）。

重型机械工作全部由自带脚本完成；Agent 的职责是**做润色决策、审阅脚本报告、诚实标注**，
不是整段重写、不是只给写作建议。

## 何时调用 / 何时不调用

- **调用**：任务明确要求润色/改写/校对/语言修改/语法修正/术语统一/语气调整/缩写规范，
  或要求交付"润色后文本＋修改说明/逐句对照/术语表"。
- **不调用**：纯内容问答（解释概念、查证事实、计算）、整篇翻译、提纲或素材生成。
  此时直接回答，**不得改写用户文本**。判断依据是任务动词：润色/改写/校对/修改 vs 回答/解释/计算/翻译。
- 不确定时：先完成阶段1任务解析，把判断依据写入 `task_profile.json` 的 `assumptions`。

## 输入与产物

输入：`/input/case.json`（含 `case_id` 与 `output_contract`）、`/input/task.md`、材料文件
（txt/md/tex/docx/pdf 等，路径与编码状况由预检报告给出）。

产物（全部写入 `/app/output`，可直接编辑与继续修改）：

| 产物 | 文件 | 说明 |
|-|-|-|
| 润色后全文 | `polished_full.md` | 保持原章节层级、公式、引用、图表编号，可直接粘回稿件 |
| 逐句修改清单 | `change_log.md` / `.jsonl` | 每句：原文、改文、修改类型（受控词表）、理由；未改句标 keep |
| 原文—改文对照 | `sentence_alignment.md`、`diff.html` | 逐句双语/双栏对照，供第三方复核 |
| 术语表 | `terminology_table.md` / `.csv` | 概念、首选写法、缩写、出现位置、来源与状态 |
| 审校报告 | `review_report.md` | 术语一致性回扫＋事实守恒检查＋逐条处置记录 |
| 预览 | `polished_full.html`、`diff.html`、`preview_polished.pdf/png`（有字体时） | 浏览器可直接打开 |
| 结构化结果 | `result.json` | 含 `case_id`、`output_contract` 全字段、状态、假设、不确定性、人工确认项 |

## 依赖与环境自适应

仅依赖 Python 3.8+ 标准库（脚本）；PDF 提取依次尝试 `pdftotext`/PyMuPDF/pypdf；
PDF/PNG 预览需要 matplotlib 与 CJK 字体，缺失时自动降级为 HTML 预览并在 `preview_report.json`
如实说明，**不生成缺字预览冒充成功**。每个脚本的报告都记录实际使用的引擎与失败原因。

## 执行流程

`<SKILL>` 为 Skill 安装目录（评测时为 `/skills/weekly-skill`）。
预算：64 次模型请求 / 900 秒 / 每次响应 ≤16384 token（含推理）。脚本合计 <30 秒；
模型调用目标 ≤14 次/案例。**任何时刻中断，/app/output 里已有 result.json 骨架与已完成产物。**

### 阶段0 预检（0 次模型调用）

```bash
bash <SKILL>/scripts/run_pipeline.sh /input /app/work /app/output
```

读取 `/app/work/brief.json`（case_id、output_contract 键、材料清单、编码问题、题面约束提示）
与 `/app/work/source_dump.md`（带稳定 ID 的逐句源文本）。若 `brief.issues` 非空，
全部原样转入 result.json 的 `uncertainty`。

### 阶段1 任务解析（≤1 次模型调用）

填写 `/app/work/task_profile.json`：

```json
{
  "language": "zh|en|mixed", "register": "期刊论文|学位论文|基金申请书|审稿回复|英文摘要|会议论文",
  "scope": "全文|指定章节（列出）", "bilingual_alignment": true,
  "term_table_source": "案例自带|脚本抽取|两者合并",
  "constraints": ["题面明确要求逐字保留的项"],
  "assumptions": ["题面未说明而自行假定的项，如目标文体不明时默认期刊论文"],
  "open_questions": ["材料不足/冲突、需人工确认的问题"]
}
```

文体不明 → 默认按期刊论文语域处理并在 assumptions 标注；材料缺失 → 记入 open_questions，
能处理多少处理多少，不编造内容。

### 阶段2 术语表（0–1 次模型调用）

```bash
python3 <SKILL>/scripts/terminology.py build --segments /app/work/source_segments.json \
    --out /app/work [--provided /input/案例自带术语表.csv]
```

脚本抽取缩写定义（"全称（ABBR）"、"中文（English, ABBR）"）与高频候选术语。
Agent 审阅 `term_table.csv`：合并案例自带术语表（冲突时案例给的优先，记入 note），
确认候选术语是否为受控概念，必要时增删行。**润色全程以此表为唯一术语依据。**

### 阶段3 逐句润色（1 次模型调用 / 块）

按 `source_dump.md` 的 ID 分块（每块 ≤2500 字、或按章节边界），逐句决策并**直接写入**
`/app/work/polish_chunks/chunk_NNN.jsonl`（每句一行 JSON，禁止整段重写式输出）：

```json
{"id":"doc-B3-P1-S2","original":"（照抄源句）","polished":"（改后句）",
 "decision":"modify","types":["grammar"],"reason":"一句话说明为什么改（≤40字）"}
```

未改句：`decision":"keep","types":[],"reason":"保留原因（如：无语病，限定强度恰当）"`。

铁律（违反即错误）：
1. **最小编辑**：只改需要改的。正确但平淡的句子不因"风格偏好"重写；整句替换仅限原句有硬错误。
2. **不许动清单**：数值、单位、统计量（p、R²、误差范围）、引用编号与 `\cite` 键、图表/公式/章节
   指向、专有名词拼写、限定词强度（可能/有望/约 ↔ may/suggest/approximately）、否定范围、
   条件句与量词（所有/部分）。术语只在术语表内统一。
3. **修改类型受控词表**（写入 types，可多选）：`grammar` 语法、`syntax` 句法、`collocation` 搭配、
   `punctuation` 标点、`spelling` 拼写、`long-sentence` 长句切分、`terminology` 术语统一、
   `abbreviation` 缩写与首次出现、`register` 语域语气、`redundancy` 冗余精简、
   `logic` 逻辑连接、`clarity` 表达清晰度、`hedging` 限定强度（原则上不出现；出现必须在 reason
   说明依据并预期被守恒检查拦截复核）、`formatting` 格式、`other` 其他。
4. **每句必录**：范围内每个句子都要有 keep/modify 记录；拿不准的标 keep 并在 reason 写
   "存疑：……"列入人工确认。
5. 详细编辑策略见 `<SKILL>/references/editing_playbook.md`；各文体语域见
   `references/style_guides.md`；限定词守恒细则见 `references/hedging_lexicon.md`。

### 阶段4 确定性审校通道（0 次模型调用 + 逐条处置）

```bash
python3 <SKILL>/scripts/assemble.py --work-dir /app/work --output-dir /app/output --bilingual
python3 <SKILL>/scripts/terminology.py check --segments /app/work/polished_segments.json \
    --table /app/work/term_table.csv --out /app/work
python3 <SKILL>/scripts/guard_check.py --source /app/work/source_segments.json \
    --chunks /app/work/polish_chunks --out /app/work
```

`guard_check.py` 对每处 modify 做机械对照：数值/单位、引用、图表指向、限定强度档位、
否定标记数、因果/相关性质。**每一条 critical 必须处置**：能改则改 polished 并重写对应
chunk 行；确认无问题则在 `/app/work/resolutions.jsonl` 追加
`{"flag_id":"…","kind":"numbers","action":"justified","note":"为什么不算改动（如单位换算已注明）"}`
——不许静默忽略。随后重跑两个检查直至 critical=0，再跑一次 assemble 把报告与处置并入产物。

### 阶段5 回读校验（1 次模型调用）

通读 `polished_full.md`（英文稿可回译关键句到中文核对语义），检查：语义漂移、漏改硬错误、
语气与目标文体贴合度、逻辑连接词是否滥用、上下文衔接。发现问题 → 修正 chunk 行 → 重跑阶段4。
同一段落重复运行时结论不得漂移：以 chunks 文件为准增量修改，不推翻已有决策。

### 阶段6 组装、预览与终检（0 次模型调用）

```bash
python3 <SKILL>/scripts/assemble.py --work-dir /app/work --output-dir /app/output --bilingual
python3 <SKILL>/scripts/render_previews.py --output-dir /app/output
python3 <SKILL>/scripts/validate_output.py --work-dir /app/work --output-dir /app/output
```

`assemble.py` 自动把 output_contract 各键映射到产物（映射不满意可在
`/app/work/contract_map.json` 显式指定，再跑一次）。`validate_output.py` 是发布闸门：
契约字段全交付或有 null_reason、change log 每条 modify 有理由、覆盖率、critical 闭环。
**validate 退出码非 0 时不得宣告完成**；确无法修复的，在 result.json 写明并保持 status=partial。

### 阶段7 诚实收尾（≤1 次模型调用）

在 result.json 中确认：`status`（complete/partial/failed，由 validate 判定）、
`assumptions`、`uncertainty`（材料缺口、编码问题、案例自带与抽取术语冲突等）、
`manual_review_required`（存疑句、未提取材料、术语表候选待确认项）、
`change_records.summary`。若题面要求的体裁/受众/格式与产物有出入，在此说明。

## 异常处置（详见 references/edge_cases.md）

- **编码混乱/乱码**：inspect 已记录编码与乱码分数；能恢复则恢复，否则该材料标注"无法可靠
  读取，需人工确认"，不猜测内容。
- **超长输入**：按章节分块逐块处理；预算不足时优先保证已处理块完整闭环（result.json 标
  partial 并列出未处理范围）。
- **公式/引用混杂（LaTeX）**：数学与 `\cite/\ref/\label` 受保护，不进入断句切分点，不改写。
- **中英日混排**：按句级语言标识处理；术语表分别登记各语言形式。
- **术语表内部冲突**：案例自带 > 领域惯例 > 频次最高；冲突与取舍记入术语表 note 与 result.json。
- **目标文体不明**：默认期刊论文语域，assumptions 标注，语域规则从 style_guides.md 取"通用学术"档。
- **重复运行**：所有产物由 chunks 文件确定性重建；重跑同一案例覆盖输出但结论一致
  （脚本无随机性；Agent 决策以已存在 chunks 为准，仅做增量修正）。

## 最小调用示例

见 `<SKILL>/examples/minimal_example.md`（含输入、命令与标注为"示例"的示意输出，非正式案例结果）。

## 维护

CHANGELOG 记录版本与规则变更；修改编辑策略时同步 `references/editing_playbook.md` 与
`evaluation/scoring_sheet.md` 中的检查点；脚本保持仅标准库依赖，新增依赖必须在 USAGE.md
写明版本与安装方式。
