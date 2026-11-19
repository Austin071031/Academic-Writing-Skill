# 引用保留与语义边界规则（boundary rules）

## 引用三形态与归一

| 形态 | 示例 | 归一 |
|-|-|-|
| 数字型 | [1]、[2-4]、[1,3] | 去空白、全角［］转半角 |
| 括号著者-年型 | (Zhang et al., 2023)、(Smith and Jones, 2021; Lee, 2020) | 全角（），；转半角、去空白、小写 |
| 叙述型 | Zhang et al. (2022) | 同上 |

译文允许把半角括号写成全角（中文学术排版惯例），其余逐字符保留；et al. 不译。
比对单位是句段内多重集：同一引用在同句段出现次数也计入。

## 六类语气词表与等强对照（部分）

| 类别 | en | zh | 等强要求 |
|-|-|-|
| possibility | may/might/could/possibly/likely/unlikely | 可能/也许/或许/有望/或 | 源有译必有其一；may 不得译成“必然” |
| suggestion | suggest/indicate/imply/appear/seem | 表明/提示/显示/暗示/似乎 | suggest→表明/提示；不得升格“证明” |
| approximation | approximately/about/around/nearly/~ | 约/大约/近/左右 | 约数标记不得丢 |
| limitation | only/solely/at most/at least/up to/no more than | 仅/只/至多/至少/最多 | 限定方向不得反（at least≠至多） |
| negation | no/not/none/never/without/absence/fail/lack | 不/无/没有/未/并非/缺乏/未见 | 否定范围一个都不能丢（高严重度） |
| certainty | prove/demonstrate/confirm/must/always/all/completely | 证明/证实/必然/一定/所有/完全 | 升格检查：源无→译文不得有 |

扩展：在 work/custom_lexicon.json 写 `{"add":{"zh":{"negation":["难以","未能"]}}}` 后
重跑 audit 即可生效（Agent 复核误报时的标准做法，记入 change_log）。

## 增译与省译

- 增译数字：译文数字在源句段无等值对应 → 高（与数字引擎分工：末位级差异归
  数字引擎的“改动”，本引擎只报无相近源的纯新增）。
- 省译：整句段未译由对齐机制报缺译；句内从句省略由 Agent 通读复核
  （本引擎不报，避免与长度启发式重复）。

## 因果与归属

- 引用必须跟随原论断句段，不得挪到相邻句段（多重集按句段比对，跨段即“缺失+新增”）。
- 因果强度词（because/therefore/thus/所以/因此）在词表 suggestion 类中按等强处理；
  把相关当因果（如把 is associated with 译成“导致”）属语气升格，Agent 复核重点。
