# dossier_rules.md — 登记簿与复核判据（与 dossier_engine.py 严格一致）

本文件是 SKILL.md 与 `scripts/dossier_engine.py` 的判据说明；修改引擎阈值时
必须同步修改本文件。所有阈值均可通过命令行参数覆盖，默认值如下。

## 1. 文本归一化与相似度

- `norm_text`：转小写，仅保留中日韩统一表意文字、英文字母与数字，其余字符删除。
- n-gram：在归一化字符串上取**字符级** n-gram 集合。
- Jaccard：`|A∩B| / |A∪B|`；空集按 0 处理。

## 2. build：登记簿抽取判据

### 2.1 定义（definitions）

满足任一模式即登记（同一 term/abbr 只保留首次出现）：

| 模式 | 示例 | 登记字段 |
|-|-|-|
| 中文全称（English full name, ABBR） | 固态电解质（solid-state electrolyte, SSE） | term=固态电解质, abbr=SSE, en=solid-state electrolyte |
| 中文全称（ABBR） | 交流阻抗谱（EIS） | term=交流阻抗谱, abbr=EIS |
| english full name (ABBR) | solid-state electrolyte (SSE) | term=尾部≤6词, abbr=SSE |
| X 是指/指的是/被定义为/定义为/记为/记作/即指 Y | 离子电导率是指… | term=X, definition=Y |
| X is defined as / is denoted as / refers to / denotes Y | … | term=X, definition=Y |
| let X denote/represent/be Y | … | term=X, definition=Y |

捕获到的前导动词（是/采用/使用/利用/称作…）会被剥除，避免「是全固态电池」
这类脏 term。缩写定义串本身即作为 definition 登记。

### 2.2 结论（conclusions）

正文中含结论动词的句子登记为结论：中文「表明/说明/证明/综上/由此可知/由此可见/
得出结论/结论是」；英文 conclude(s)/conclusion/demonstrate*/show(s/ed/n) that/
indicate* that/suggest* that。
`key_numbers` 抽取带单位数值：`\d+(\.\d+)?` + 单位（%、°C/℃/K、mS/cm、h/min/s、
V/mV、Hz/kHz/MHz、MPa/GPa/Pa、nm/μm/mm/cm、mA/mAh/A、g/mg/kg、mol、wt%/at%、
rpm、W/kW、J/kJ、eV/keV 等）。heading/图表注/公式注/参考文献段不抽取。

### 2.3 材料使用（material_usage）

- 材料文件识别：文件名匹配 `(fact|facts|note|notes|reading|material|materials|
  data|dataset|材料|笔记|摘录|数据|事实)`（大小写不敏感），可用
  `--materials-regex` 覆盖；未匹配到时 material_usage/omissions 为空并打印 WARN。
- 材料段落：材料文件中 kind∈{body,list,appendix,footnote} 且归一化长度 ≥8 的段落。
- 使用判定：材料段落与任一**章节**段落（同类 kind）的 **2-gram Jaccard ≥ 0.15**
  （`--usage-threshold`）记为被该章节引用/复述。
- omissions：无任何使用记录的材料段落——「未使用材料清单」。

### 2.4 术语首现（glossary_first_use）

- 对全部定义 term/abbr 与全文中观察到的全大写 token（`[A-Z][A-Za-z0-9]{1,9}`，
  排除内置停用表 GB/ISO/ASTM/单位等）记录首现 pid。
- `detached_use=true`：全大写缩写的首现 pid 早于其定义 pid（使用早于定义 =
  脱节候选），在 dossier.md 中以 ⚠ 标出。

### 2.5 图表 caption（captions）

kind∈{figure_note, table_note, caption} 且以「图N/表N/Fig N/Table N」开头的段落，
登记 (kind, number, pid)。供 overlap 的悬空引用检查与编号续编。

## 3. brief：上下文摘要判据

- 相关性：目标章节标题与每条目的 **2-gram Jaccard**；各桶内按相关性降序排列。
- 五个桶（按优先级）：① 前文相关定义 → ② 前文已下结论 → ③ 未用材料提醒 →
  ④ 已被前文使用的材料 → ⑤ 已有图表 caption。
- 预算：`--budget-chars`（默认 3000）按字符数截断；每桶的「候选/纳入/截断」
  数量如实记录在 brief 末尾「截断记录」一节——截断不静默。

## 4. overlap：复核判据

### (a) 重复论述（repeated_exposition）

- draft 句子（归一化长度 ≥10）与已有**章节**（不含材料文件）句子的
  **4-gram Jaccard ≥ 0.6**（`--overlap-threshold`）记为重复论述对，
  每句只报最高分的一个匹配。

### (b) 重复结论（repeated_conclusions）

- draft 中的结论句（同 2.2 动词表）与 dossier conclusions 比较：
  - **同主语**：共享任一已定义 term/abbr，或共享化学式/复合大写实体
    （`[A-Z][a-z]?(\d*[A-Z][a-z]?)+\d*`，如 Li6PS5Cl），或句子 2-gram
    Jaccard ≥ 0.25；
  - **重复声明**：同主语且（共享至少一个带单位关键数值，或 4-gram
    Jaccard ≥ 0.3）。
- 两者同时满足才报——「新结论引用旧数值作对比」不算重复（主语不同即豁免）。

### (c1) 脱节：未定义缩写（undefined_abbrs）

- 缩写候选：draft 中**全大写且含 ≥2 个字母**的 token（排除化学式、批次号、
  内置停用表）。
- 判定：不在 dossier 定义缩写表、也未在 draft 自身定义句中定义 → 登记。
  - **critical**：前文（glossary_first_use）从未出现 → 真脱节，必须补定义；
  - **warning**：前文出现过但同样未定义 → 沿用风险，建议补定义。
- critical 计入 `critical_total`，影响 verdict；warning 只提示。

### (c2) 脱节：悬空图表引用（dangling_figtab）

- draft 中「图N/表N/Fig N/Table N」引用，若在 dossier captions 与 draft 自身
  caption 中均无对应编号 → 登记为悬空引用（critical）。

### (d) 未用材料提醒（omission_reminders）

- dossier omissions 与 draft **最相关段落**（逐段取最大值的 **2-gram
  Jaccard ≥ 0.1**，`--remind-threshold`）→ 列出提醒纳入。
- 按段落比较而非全文比较，避免长草稿与短材料条目规模悬殊稀释相关性。
- 提醒非 critical，但应逐条处理或登记理由（红线三）。

## 5. verdict 判定

| verdict | 条件 |
|-|-|
| CLEAN | critical_total=0 且无材料提醒 |
| PASS_WITH_REMINDERS | critical_total=0，有材料提醒（可交付，提醒须逐条处理或登记） |
| HAS_ISSUES | critical_total>0（重复论述/重复结论/critical 未定义缩写/悬空图表），必须修复复跑或降级 partial |

## 6. 已知边界（诚实声明）

- 字符 n-gram 是字面启发式：语义复述但字面完全不同的重复论述可能漏检；
  反之大段公式化套话（如完全相同的实验步骤句）会被按重复论述命中——这正是
  设计意图（学位论文中实验步骤也不应整段照抄）。
- 定义/结论抽取基于模式匹配，非常规表述（「所谓 X，乃…」）可能漏登记；
  dossier 为空类时不臆造，见 SKILL.md 异常处置表。
- 相似度不支持跨语言（中文句与英文句字面无重合时漏检）。
