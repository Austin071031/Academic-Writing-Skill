---
name: academic-polish-surgical-rubric
description: 学术语言润色 Skill（零脚本手术式方法论 + 评分细则自审闭环：编辑规程在提示内闭环，交付前把题面评分细则变成逐条核对表自审，处理项覆盖清单作硬闸门，随稿交付 rubric_audit.md 复核地图，漏项在交付前被拦截）。当任务要求润色、改写、校对、语法修正、术语统一、缩写规范、语气调整、中译英语言质量提升，并要求交付润色后全文与逐句修改说明时使用。触发示例："把这段润色一下，告诉我每句改了什么""按期刊语气改这段话"。不触发：纯内容问答、事实查证、计算、整篇翻译——直接回答，不得擅自改写原文。产物：/app/output 下 polished 全文、逐句修改卡、术语表、守恒自查表与含 case_id/output_contract 的 result.json。
---

# academic-polish-surgical-rubric：评分细则自审闭环的零脚本润色（v3.4.0）

**v3.4.0 相对父辈 v1.2.0（得分 69.67）的唯一新增**：评分细则自审闭环——交付前
按 references/rubric_audit.md 把题面四维评分点逐条核对（状态+证据位置），
处理项覆盖清单（指定章节/术语表/缩写首现/双语对照/修改清单/守恒自查/契约字段/
诚实标注）作硬闸门，随稿交付 rubric_audit.md 复核地图。编辑决策规程与父辈一致。
提分目标：实际效果的"任务完成度/结果完整性"（漏项清零）与"结果可核验性"
（评审可按复核地图直接验证）。

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
1. **术语扫**：术语表里每个概念在改文中是否只有一种写法（缩写全称共现的首现句除外）；
   缩写是否首现有全称。发现漂移 → 改。
2. **守恒扫**：逐句对照修改卡，问"数字、单位、引用、图表指向、限定词、否定、因果
   是否与原文一致？"不一致 → 要么改回去，要么在卡的"依据"里写明理由并列人工确认。
3. **语域扫**：对照 references/register.md 的目标文体清单逐条过。

### 交付（第 4 步）

全部写入 `/app/output`（格式见下）。**v3.4.0 新增：评分细则自审（交付前硬闸门）**——
按 references/rubric_audit.md 的格式写 `/app/output/rubric_audit.md`：
1. 先过"处理项覆盖清单"八项硬闸门，任何一项未勾先补救；
2. 再填四维自审表，每条给"达成/部分/未达"状态与可定位证据（文件+位置，不许写"略"）；
3. 未达项补救不了就如实写明原因，并同步进 result.json 的 uncertainty。
然后写 result.json，把 rubric_audit.md 列入 artifacts。

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

**`terminology_table.md`** — 概念 / 首选写法 / 缩写 / 出现位置 / 来源（案例自带或文本抽取）
/ 状态（已定/候选/冲突待确认）。

**`sentence_alignment.md`**（任务要求双语对照时）— 原文/改文/类型/理由 逐句四列表。

**`conservation_check.md`** — 守恒自查表：数值与单位、引用、图表指向、限定强度、
否定范围、因果性质 六行，每行写"一致/有变动及处置"，附存疑句 ID。

**`rubric_audit.md`**（本版核心交付物）— 评分细则自审表：四维评分点逐条状态 +
证据位置 + 处理项覆盖清单八项硬闸门。给评审的复核地图，未达项如实标注。
格式见 references/rubric_audit.md。

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

- references/lexicon.md：限定强度三档词表（中英）、因果/相关对照、禁动清单详解。
- references/register.md：五种文体的语气规则与该做/不该做。
- references/chinglish.md：中式英语 12 类典型病灶与修法。
- references/rubric_audit.md（本版核心）：评分细则自审规范与覆盖清单。
- examples/minimal_example.md：最小输入→调用→示意输出（标注为示例）。

## 稳定性与边界

- 重复处理同一段：以已写的修改卡为准做增量修正，不推翻先前决策。
- 超长输入：按章节分块；先完成块内闭环（卡+守恒扫），再进下一块；预算不够时
  result.json 记 partial 并列出未处理章节。
- 中英日混排：按句语言分别处理，术语表各语言形式分别登记。
- 无脚本依赖：任何环境可执行；无版本、无安装、无路径问题。
