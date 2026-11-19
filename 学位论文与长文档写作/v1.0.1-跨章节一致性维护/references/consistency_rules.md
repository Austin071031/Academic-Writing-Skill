# 跨章节一致性判据表（consistency rules）

本表与 `scripts/consistency_engine.py` 顶部常量一一对应；改阈值必须两边同步。

## 1. 术语候选提取（scan → glossary_candidates.json）

### (a) 缩写定义型
| 模式 | 正则（语义） | 示例 |
|-|-|-|
| 中文（english full, ABBR） | 2–30 字中文 + 括号内英文全称 + 逗号 + 2–10 位大写缩写 | 全固态电池（all-solid-state battery, ASSB） |
| 中文（english full） | 同上，无缩写 | 固态电解质（solid-state electrolyte） |
| 中文（ABBR） | 括号内全大写且无空格 → 视为缩写，definition 记 null | 交流阻抗谱（EIS） |
| ABBR (english full) | 2–10 位大写缩写 + 括号内小写开头英文全称 | PSCs (perovskite solar cells) |

中文术语左侧黏着的动词/虚词（是/为/称/即/采用/通过/基于/的/了 等，见引擎
`ZH_LEAD_STRIP`）自动剥离，剥离后不足 2 字则丢弃该候选。
每条候选回扫全文，统计 term/abbr/definition 三种写法出现的 pid 列表与总次数。

### (b) 引号/书名号型
`「…」『…』“…”《…》` 内 2–30 字内容，出现 ≥2 次才收。

### (c) 高频复合词
- 中文：4–8 字 n-gram（`ZH_NGRAM_RANGE`），出现 ≥3 次（`HFREQ_MIN_COUNT`）；
  被更长且同频词组包含的短词组丢弃（"两步烧结工艺"在则"两步烧结"不单列，
  除非其独立频次更高）。
- 英文：2–3 词短语（`EN_PHRASE_RANGE`），去停用词（`EN_STOP`）后统计，≥3 次。
- 每类输出上限 60 条（`MAX_CANDIDATES`），按频次降序。

## 2. 规范化规则（normalize）

比较写法是否"同一概念"前统一执行：
1. Unicode NFKC（全角→半角）；
2. 小写化；
3. 连字符归一（– — − → -），空白/下划线→单连字符；
4. 英文粗单复数归一（词尾 s 去除、ies→y）。

规范化后相同 = 同一写法；与 canonical 规范化不同 = 异写。

## 3. 交叉引用一致性（scan → xref_audit.json）

- 定义段：kind ∈ figure_note / table_note / equation_note / caption，且段首匹配
  `图N-N / Fig N-N / 表N-N / Table N-N / 式(N-N)`。
- 引用：正文段 xrefs（由 parse_chapters 提取）中 figure/table/equation 三类；
  定义段自身不计引用。
- target 归一：`3.1` / `3-1` / `3–1` 视为同一目标。
- **dangling**（critical）：正文引用无对应定义段 → validate_output FAIL。
- **unreferenced**（warn）：有定义段但全文无正文引用。
- **编号连续性**：同一文件（章）内同类编号按文档序应严格递增；非递增或重复
  记入 numbering。

## 4. 结论句矛盾候选（scan → contradiction_candidates.json）

- 结论句：正文段中长度 ≥8 且含结论关键词（表明/说明/证明/综上/得出/可见/由此/据此/
  conclude/show/demonstrate/indicate/suggest/prove，`CONCL_WORDS`）的句子。
- 主语 n-gram：去掉结论关键词与"本文/本研究/我们/实验/结果"等套话后，
  取中文 3-gram ∪ 英文词（>2 字母）集合（`subject_ngrams`）。
  中文"表明"类词主语可在关键词前（"两步烧结表明…"）或后（"结果表明，两步烧结…"），
  故取两侧并集。
- 重叠度 = |A∩B| / min(|A|,|B|) ≥ **0.3**（`SUBJECT_OVERLAP_MIN`）。
- 极性：句中含 不/未/无法/不能/并无/并未/no/not/fail/n't/cannot/never
  （`NEG_WORDS`）为 negative，否则 positive。
- 候选条件：跨文件（章）+ 重叠 ≥0.3 + 极性相反。**引擎只出候选，不自动判错**；
  由 Agent 结合条件、对象、时间演化逐对裁决。

## 5. 异写统计（glossary → consistency_report）

- 逐段落对各术语的 {canonical}∪variants 做字面查找；重叠命中只计最长写法
  （"两步烧结工艺"内的"两步烧结"不重复计数）。
- **定义处豁免**：definition_pid 段落中"中文（english, ABBR）"整体命中不计入
  出现数与异写数（学术惯例：定义处同时出现全称与缩写是规范行为）。
- 异写率 = 异写出现数 / 总出现数（豁免后）。
- 符号冲突：
  - `double_definition`：同一 canonical 在 review 中有两个不同 definition_pid；
  - `symbol_clash`：同一缩写（2–10 位大写开头）归属两个不同 canonical。

## 6. 影响面分析（impact → impact_report）

- `--changed-term X`：受影响 = 段中含 X 或其 glossary 认可写法的全部 pid
  + 与受影响段落结论句主语重叠 ≥0.3 的其他结论句段落。
- `--changed-sid C01-S001`：受影响 = 该节全部段落 + xref 指向该文件内图表/公式
  定义的段落 + "第X章/第X节"引用指向该文件标题编号的段落 + 与该节结论句主语
  重叠 ≥0.3 的段落。
- 中文数字章号（一~十）自动转阿拉伯数字比对。
