---
name: academic-polish-surgical-terms
description: 学术语言润色 Skill（零脚本手术式方法论 + 术语双语对齐深化：编辑规程在提示内闭环，仅用一个扫描脚本做全篇术语漂移回扫；术语表中英双语形式成对绑定，跨章节漂移与缩写首现违规无处可藏）。当任务要求润色、改写、校对、语法修正、术语统一、缩写规范、语气调整、中译英语言质量提升，并要求交付润色后全文与逐句修改说明时使用。触发示例："把这段润色一下，告诉我每句改了什么""按期刊语气改这段话"。不触发：纯内容问答、事实查证、计算、整篇翻译——直接回答，不得擅自改写原文。产物：/app/output 下 polished 全文、逐句修改卡、术语表、守恒自查表与含 case_id/output_contract 的 result.json。
---

# academic-polish-surgical-terms：术语双语对齐的零脚本润色（v3.1.0）

**v3.1.0 相对父辈 v1.2.0（得分 69.67）的唯一新增**：术语治理升格为一流交付物——
润色前建双语对齐术语表（中英形式成对绑定），润色后用唯一脚本 term_scan.py 做
全篇漂移回扫（同概念多写法并存=critical，缩写首现=warning），交付
terminology_table.md 与 term_consistency_report.md。编辑决策规程与父辈一致。
提分目标：实际效果的"结果完整性"（术语表建全、缩写首现统一、双语对照）与
创新增益中"术语表驱动的全篇一致性回扫、双语术语对齐"两项具名能力。

设计哲学：润色的质量瓶颈在**编辑决策**，不在工具链。本 Skill 不运行任何脚本，
把一套完整的手术规程压进提示：四步流程、七问决策法、受控词表、禁动清单、
逐句修改卡格式、守恒自查表。Agent 读完即可对任意长度、任意学科的学术文本执行
一致的精修，不因为工具编排失败而中断。

四条承诺：**改得对**（硬错误真消除）、**说得像**（贴合目标文体）、**没改坏**
（限定强度/数据/单位/引用/图表指向守恒）、**讲得清**（每处修改有原文、改文、类型、理由）。

## 何时调用 / 何时不调用

- 调用：任务动词是 润色/改写/校对/修改/统一术语/规范缩写/调整语气，或要求交付
  "改后文本＋修改说明/逐句对照"。
- 不调用：任务是 回答/解释/查证/计算/整篇翻译。此时直接回答，**一个字都不许改**。

## 材料读取（第 0 步，必做）

1. 读 `/input/case.json`（取 `case_id` 与 `output_contract` 全部键名）与 `/input/task.md`。
2. 按类型读材料：txt/md/tex 直接读；docx 用 unzip 提取 word/document.xml 后读 `<w:t>`；
   pdf 用 `pdftotext -layout`（无则用 PyMuPDF/pypdf）。编码按 UTF-8 → GB18030 顺序试，
   仍乱码则该文件标注"无法可靠读取"进 result.json 的 manual_review_required，**不猜内容**。
3. 材料缺失/无法提取：能处理多少处理多少，result.json 如实标注 status=partial。

## 任务画像（第 1 步，一段话写下即可）

- 语言（中/英/混排）、目标文体（期刊论文/学位论文/基金申请书/审稿回复/英文摘要；
  不明 → 默认期刊论文并注明这是假设）、润色范围（全文或指定章节）、是否要双语对照、
  是否有案例自带术语表（有则全篇以它为准，冲突记入 result.json uncertainty）。
- 把画像原样写入 `result.json` 的 assumptions 与 constraints，不藏在推理里。

## 术语表（第 1.5 步，必做，本版核心）

逐句润色之前，通读全文建立双语对齐术语表 `/app/work/term_table.csv`
（格式与治理规则见 references/term_governance.md）：concept/preferred（中英用 / 分隔）/
variants/first_use/status/note。案例自带术语表优先，冲突记 note。
**此后每一处术语、缩写、大小写、连字符都以该表为唯一依据；中英形式成对统一。**

## 手术主流程（第 2 步：逐句；第 3 步：回扫；第 4 步：交付）

### 逐句七问（每句顺序过一遍，全部答完再决定是否动笔）

1. **硬错误？** 语法/句法/搭配/标点/拼写错误存在吗？→ 有：改，类型记 grammar/syntax/
   collocation/punctuation/spelling。
2. **悬垂或长句失控？** 修饰语无所依、一句三层嵌套 → 改，类型 syntax 或 long-sentence。
3. **术语/缩写不一致？** 同一概念多种写法、缩写首现无全称 → 对照术语表改，类型
   terminology/abbreviation。
4. **语域错位？** 口语化（但是/比如/做了）、宣传化（very excellent/国际领先/首次且
   无证据）、人称误用（中文稿"我们"作主语、英文正文 *I*）→ 按文体指南改，类型 register。
5. **冗余或逻辑滥用？** *in order to*、*due to the fact that*、"值得注意的是"空转、
   *Moreover* 一段三个 → 删，类型 redundancy/logic。
6. **清晰度欠账？** 指代不明、*this/that* 悬空、中文长定语链 → 补/拆，类型 clarity。
7. **以上皆无 → keep。** 正确但平淡的句子**不改**；改它只是换一种说法，不是润色。

决策后写**修改卡**（见格式节）。改动必须满足：
- **最小编辑**：只动需要动的词与结构；整句重写仅限原句有硬错误且局部修不好。
- **禁动清单**：数值、单位、统计量、引用编号与 \cite 键、图表/公式/章节指向、
  专有名词拼写、限定词强度（可能/有望/约 ↔ may/suggest/approximately）、否定范围、
  量词（所有/部分）、因果与相关的区分。这些一个字都不许动；术语只在术语表内统一。

### 全篇回扫（逐句完成后必做，不许省）

对改后全文做三遍回扫，各记一笔：
1. **术语扫**（本版用脚本兜底，不只靠读）：

```bash
python3 /skills/weekly-skill/scripts/term_scan.py --table /app/work/term_table.csv \
    --text /app/output/polished.md --out /app/work
```

   critical（同概念多写法并存）必须统一为 preferred 后重跑，直至 critical=0；
   报告复制到 `/app/output/term_consistency_report.md` 随稿交付。
2. **守恒扫**：逐句对照修改卡，问"数字、单位、引用、图表指向、限定词、否定、因果
   是否与原文一致？"不一致 → 要么改回去，要么在卡的"依据"里写明理由并列人工确认。
3. **语域扫**：对照 references/register.md 的目标文体清单逐条过。

### 交付（第 4 步）

全部写入 `/app/output`（格式见下），然后写 result.json。

## 产物格式（严格按此，可直接编辑）

**`polished.md`** — 润色后完整文本：保持原章节层级、公式、引用、图表编号，可直接粘回。

**`change_log.md`** — 逐句修改卡（每句一张，keep 也要卡）：

```markdown
### 句 P2-S3
- 原文：The results of the experiment shows a improvement.
- 改文：The experimental results show an improvement.
- 决策：modify ｜ 类型：grammar, collocation
- 理由：主谓一致（results 复数→show）；冠词 an；of 短语名词化缩合为形容词。
```

**`terminology_table.md`** — 双语对齐术语表：概念 / 首选写法（中文/English 成对） /
变体写法 / 首现位置 / 状态 / 备注；格式与治理规则见 references/term_governance.md。

**`term_consistency_report.md`** — term_scan.py 的全篇回扫报告（critical 必须为 0，
残留 warning 须注明理由）。

**`sentence_alignment.md`**（任务要求双语对照时）— 原文/改文/类型/理由 逐句四列表。

**`conservation_check.md`** — 守恒自查表：数值与单位、引用、图表指向、限定强度、
否定范围、因果性质 六行，每行写"一致/有变动及处置"，附存疑句 ID。

**`result.json`** — 结构：

```json
{"case_id":"<原 case_id>","status":"complete|partial|failed",
 "output_contract":{"<原契约键>":{"delivered":"<产物文件名>"} 或 {"delivered":null,"null_reason":"…"}},
 "artifacts":{"polished":"polished.md","change_log":"change_log.md","terminology":"terminology_table.md"},
 "change_records":{"sentences_total":N,"modified":N,"kept":N,"by_type":{"grammar":3}},
 "assumptions":[],"uncertainty":[],"manual_review_required":[]}
```

`output_contract` 必须覆盖 case.json 的全部键；交不出就写 null_reason，不许空着。

## 理由质量标准（讲得清的命门）

- 每条理由指向具体语言现象：哪个词、哪种结构、哪条规则。≥8 字。
- 禁止："更通顺""更规范""语言优化""提升可读性"这类说不出改的是什么的话。
- 存疑句：decision=keep，理由以"存疑："开头，句 ID 进 manual_review_required。

## 参考表（按需取阅，不必全读）

- references/term_governance.md（本版核心）：双语对齐术语表格式、治理规则、回扫流程。
- references/lexicon.md：限定强度三档词表（中英）、因果/相关对照、禁动清单详解。
- references/register.md：五种文体的语气规则与该做/不该做。
- references/chinglish.md：中式英语 12 类典型病灶与修法。
- examples/minimal_example.md：最小输入→调用→示意输出（标注为示例）。

## 稳定性与边界

- 重复处理同一段：以已写的修改卡为准做增量修正，不推翻先前决策。
- 超长输入：按章节分块；先完成块内闭环（卡+守恒扫），再进下一块；预算不够时
  result.json 记 partial 并列出未处理章节。
- 中英日混排：按句语言分别处理，术语表各语言形式分别登记。
- 无脚本依赖：任何环境可执行；无版本、无安装、无路径问题。
