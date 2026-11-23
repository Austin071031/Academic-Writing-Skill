# 术语表格式与治理规则（term table guide）

## 表结构（terminology.py 输出 term_table.csv，列固定）

| 列 | 含义 |
|-|-|
| concept_key | 概念内部键（`zh:均方根误差`、`provided:…`、`cand:…`、`undef:…`） |
| preferred_form | 首选写法（全篇统一目标） |
| abbreviation | 对应缩写（无则空） |
| variant_forms | 源/改文中出现的全部写法及次数 |
| occurrences | 出现位置（句子 ID，前 8 处） |
| source | 来源：缩写定义 / 案例自带术语表 / 高频候选 / 未定义缩写 |
| status | `case_provided` > `defined` > `candidate`；冲突未决记 `conflict` |
| note | 取舍依据、冲突说明、待确认项 |

## 治理规则

1. **优先级**：案例自带术语表 > 领域通行惯例 > 源文本频次最高写法 > Agent 提议
   （提议必须写入 note 供人工确认）。
2. **一对一律**：一个概念一行；同义多写法全部列入 variant_forms，润色后只保留
   preferred_form（缩写全称共现的首现句除外）。
3. **缩写首现**：缩写首次出现须与全称同现（"全称（ABBR）"或"全称（English, ABBR）"）；
   check 阶段会对"缩写先于全称出现"报 warning。
4. **跨章漂移**：同一概念在摘要/引言/方法中的写法必须一致；check 阶段做全篇回扫，
   多种写法并存报 critical。
5. **新增写法**：润色中确需引入源文本没有的形式（如补英文全称）时，把它加入
   variant_forms 并在 note 记录原因，避免下一轮 check 误报。
6. **双语对齐**：中英双语稿，概念行同时登记两种语言形式（preferred_form 用"中文 /
   English"双写法），check 分别核对。

## 冲突处置流程

发现案例自带表与源文本写法冲突 → 以案例自带表为准统一文本 → term_table.csv 的 note
记录"源文写法 X 按案例术语表统一为 Y" → result.json 的 uncertainty 登记该冲突。
发现候选术语误抽（非术语）→ Agent 直接从表中删除或标注 `status=candidate` 并在 note
说明"非受控概念，人工可删"。
