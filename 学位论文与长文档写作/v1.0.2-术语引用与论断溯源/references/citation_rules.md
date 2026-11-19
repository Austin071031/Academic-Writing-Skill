# 引用与论断溯源判据（citation_rules.md）

本文件是 `trace_engine.py` 与 SKILL.md 共用的判据定义。引擎行为与本文件保持一致；
人工评审可据本文件复核引擎输出。

## 1. 论断抽取与引用绑定（bind）

- **论断记录**：每条含引用标记的正文段落抽为一条论断：
  `{claim_id, pid, sentence, cite_marks, entry_ids, status}`。
  `sentence` = 段落中包含引用标记的句子（拼接）；heading / reference_list / caption 段不入池。
- **绑定规则**（按标记样式）：
  | 样式 | 规则 |
  |-|-|
  | numeric `[n]` / `[1-3,5]` | 按文献表序号映射：`[n]` → records[n-1]；`n > 条目数` 即越界 unresolved |
  | author_year `（作者, 年）` | 作者姓规范化（小写、去点号/空格/连字符；先剥离「等/et al」再判断语种；中文取姓含复姓表）+ 年份精确匹配（取 4 位年，忽略 a/b 后缀） |
  | latex `\cite{key}` | key 与 BibTeX 条目 key 精确匹配（大小写不敏感） |
  | footnote_md `[^label]` | label 与条目 key 匹配 |
- **status**：`bound`（全部标记命中）/ `partially_bound`（部分命中）/
  `unbound`（全部未命中，**critical**，即"引用了不存在的文献"）。
- partially_bound 与 unbound 均进入审查报告 (a) 节，severity=critical。

## 2. 数值一致性判据（verify-b）

- **遮蔽规则**（以下数字不参与核对）：图表编号（图3-1、Table 2）、章节编号（第1章、3.1.2）、
  年份（19xx/20xx）、引用标记本身、URL/DOI、紧接字母/数字的化学式与型号内嵌数字
  （Li6PS5Cl、B7：数字前邻字母或数字即不抽取）。
- **判定**（对论断句中每个事实数值）：
  - `verbatim`：材料文本（同样遮蔽后）含相同数值（相对容差 1e-6）；
  - `derived`：与材料单值偏差 ≤1%；或与材料值为百分比换算关系（×/÷100，±1%）；
    或等于材料两值四则运算结果（±1%，材料数值池 >60 时禁用两值推导防误命中）；
  - `unverified`：其余。**unverified 不得静默**——必须进入报告与 evidence_map。
- **豁免**：含「目标/拟/旨在/计划/expected」等意图词的句子属研究目标而非事实论断，不核对。

## 3. 语气边界判据（verify-c）

- 语气强度阶梯：L4 证明/证实/完全解决/彻底解决/prove/confirm
  > L3 表明/说明/demonstrate/show > L2 显示/indicate > L1 可能/有望/may/might/suggest。
  无语气词的直接陈述按 L3（平实断言）计。
- **材料句匹配**：按关键词重叠（拉丁词 + CJK 二元组）+ 数值重合（×3 权重）选取得分最高
  且 ≥2 分的材料句；无匹配则跳过语气检查（不报）。
- **overstated（升格）**：`claim_level ≥ 4 且 claim_level − material_level ≥ 2`。
  典型：材料「可能改善」→ 论文「证明/完全解决」。
  L3「表明」对 L1 材料不报——直接陈述属正常转述，避免误报。
- **negation_flip（否定翻转）**：论断含「解决/克服/消除/solved/eliminate」类断言，
  而匹配材料句含「挑战/困难/问题/尚未/仍/challenge/remain」类表述。
- 两类均只标为**候选**，供 Agent 对照原文裁决；引擎不自动改写。

## 4. 漏引判据（verify-d）

触发条件（同时满足）：正文段、无引用标记、含事实数值、非意图句，且
（至少一个数值 unverified **或** 含「已有研究/据报道/文献表明/reported」等引述型措辞）。
- 数值全部可溯源到材料的段落（如本实验方法参数）不报，避免把自有数据当漏引。
- 推荐候选：论断句关键词与条目 标题+刊名 重叠计数，取 top3（score>0）；
  仅供 Agent 决定是否补引，引擎不自动插入引用。

## 5. 术语与缩写统一判据（Agent 执行，引擎辅助）

- 同一概念全文只用一种中文术语写法（如「固态电解质」不与「固体电解质」混用）；
- 缩写首次出现处须「全称（英文, 缩写）」定义，之后统一用缩写；
  未定义即使用、或重复定义，均记入 change_log 或 uncertainty；
- 术语统一不得改变论断含义与数值；只统一写法。

## 6. 文献表渲染与一致性（render_refs）

- 默认样式 `gbt2015_numeric`（GB/T 7714-2015 顺序编码制）；顺序 = 正文首次出现顺序
  （work/order.json，可由 --order 覆盖），未被引用条目按库序附后。
- 交叉核对（经 cite_engine audit）：正文编号越界 = critical；1..max 有缺口 = critical；
  样式混杂 = 报告。
- 交付闸门（validate_output）：references.md 编号必须连续；output 内全部 .md 的
  `[n]` 引用必须 ⊆ references.md 编号集合（双向一致）。
