# 术语表 schema、异写判据与跨文体替换策略（与 terminology_engine.py 常量一致）

## term_table.json schema

顶层为 `{"meta": {...}, "terms": [...]}` 或直接是条目数组。每条：

| 字段 | 类型 | 说明 |
|-|-|-|
| term_id | str | T001… 由引擎编号，审定时保持稳定 |
| canonical | str | 标准说法：全文与所有产物的基准写法（通常取源文全称/最高频写法） |
| variants | [str] | 源文中出现的异写/全称/缩写/大小写连字符变体 |
| kind | str | zh_term（中文术语）/ acronym（大写缩写）/ symbol（化学式、材料牌号） |
| first_expand | bool | 该受众下缩写首次出现是否必须展开（本领域同行可 false） |
| cross_genre | dict | 三栏：科普文章 / 新闻通稿 / 项目申报材料 的替换建议（项目申报材料通常"保留"） |
| note | str | 检测依据、歧义标注、待确认事项 |

## 异写判据（candidates）

1. **全称↔缩写配对**：源文"全称（ABBR）"（RE_EXPAND_FW）与"ABBR（全称）"（RE_EXPAND_RV）；
   全称捕获后剥离前导动词/虚词（采用/通过/本研究……，RE_LEAD_STRIP）。
2. **中文异写**：相似度 ≥ **0.70**（SIM_THRESHOLD），取三者最大：
   编辑相似度（SequenceMatcher.ratio）、最长公共子串覆盖率、共享字符覆盖率（2·|共有字|/(len a+len b)）。
   例：固态电解质/固体电解质 = 0.80 → 同簇。长度差 >3 不并簇（防"X 体系"误并）。
3. **大小写/连字符/空格变体**：拉丁 token 归一化（小写、去非字母数字）同键归并。
   例：Li-ion / Li ion / LI-ION 同键。
4. 化学式用独立正则识别（`(元素符号+下标){2,}`，支持小数计量 LiNi0.8Co0.1Mn0.1O2），
   单位 token（mS/cm、mAh/g 等）与普通英文词不收。
5. 中文术语抽取：核心词锚定（电解质/电池/界面/材料…28 个）+ 左扩展 ≤6 字，
   遇虚词/动词停止；仅保留"边界处出现 ≥1 次"或"全文出现 ≥2 次"者，防跨词界碎片。

## audit 检查项与严重级

| 类型 | 级别 | 判定 |
|-|-|-|
| variant_used | warn | 使用了非 canonical 的中文/符号异写（缩写形式由展开规则单独判） |
| acronym_not_expanded | critical | first_expand=true 的缩写出现，但全文无"全称（缩写）"或"缩写（全称）" |
| symbol_conflict | critical | 同一缩写两种展开（后缀包含视为同一展开），或文中展开与术语表登记冲突 |
| cross_file_inconsistent | warn | 同一概念在不同产物的主导说法不同（主导=有效出现次数最多，并列取短形式） |
| unlocked_change | warn | 未登记说法与某 canonical 相似度 ≥0.70 |

计数用"有效出现"：被更长形式包含的匹配不计（如"固态电解质"之于"硫化物固态电解质"）。
exit 0 = 无 critical（PASS）；2 = 有 critical；1 = 输入错误。

## 跨文体替换策略（cross_genre 三栏默认）

| kind | 科普文章 | 新闻通稿 | 项目申报材料 |
|-|-|-|-|
| acronym（全称已知） | 首次"全称（缩写）"+通俗解释，之后可缩写 | 首次"全称（缩写）"，之后可缩写 | 保留缩写，首次展开一次 |
| acronym（全称未知） | 中文描述性说法替换+待确认 | 中文描述性说法替换+待确认 | 保留缩写+待确认 |
| symbol（化学式/牌号） | 保留，首次附中文名/说明 | 保留，必要时附中文名 | 保留 |
| zh_term | 统一 canonical，首次给解释/类比 | 统一 canonical | 保留 |

## 术语歧义处置

两种写法无法判定是否同一概念（特指 vs 泛指）时：**不强行收敛**，表内分立条目、
note 标注歧义，稿件保留源文原说法，入 manual_confirmations 请作者确认。
