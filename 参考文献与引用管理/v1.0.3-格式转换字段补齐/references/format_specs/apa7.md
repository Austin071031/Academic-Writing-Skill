# APA 第7版 规范数据文件（规范示例整理）

> 数据文件：`scripts/convert_engine.py` 解析下方"机器可读参数"节；正文供 Agent 与人参考。

## 机器可读参数（convert_engine 解析，请勿改动键名）

- template: "{authors} ({year}). {title}. *{venue}*, *{volume}*({issue}), {pages}. https://doi.org/{doi}"
- label: ""（悬挂缩进，不编号）
- max_authors: 20（21 人及以上：前 19 人 + … + 末位作者）
- zh_truncate_suffix: ""（APA 不使用"等"；中文条目作者照录，必要时附拼音）
- en_truncate_suffix: ", … {last_author}"
- punct_zh: halfwidth（APA 条目内部一律半角，含中文题名）
- punct_en: halfwidth
- western_name_form: "Surname, I. I.（姓全称 + 名首字母加点，不臆造中间名）"
- doi_form: "https://doi.org/{doi}"

## 条目模板字符串

期刊：`Author, A. A., & Author, B. B. (Year). Title of article: Sentence case. *Journal Name*, *volume*(issue), pages. https://doi.org/xxx`
会议：`Author, A. A. (Year). Title. In *Proceedings Title* (pp. xx-xx). Publisher.`
专著：`Author, A. A. (Year). *Book title*. Publisher.`

## 作者截断规则

- 20 人以内全列，姓名间用逗号、末位前加 `&`。
- 21 人及以上：列前 19 人，`…`，再列最后 1 人（**不得用 et al. 于文献表**；et al. 仅限文内引用）。
- 西文姓名：`Smith, John` → `Smith, J.`（名仅取首字母，不臆造中间名）。
- 题名用 sentence case（句首、专名、冒号后大写）；刊名与卷号斜体。

## 标点规则

- 全部半角；作者-年份间用句点；年份圆括号半角。
- 中文条目题名/刊名保持中文，但条目结构标点仍为半角；DOI 写为 `https://doi.org/...` 原样保留。

## 类型标识表

APA 不使用 `[J]/[C]` 类型标识；由条目类型（期刊/会议/书）模板区分，不标注类型字母。

## 示例条目（规范示例，非真实文献）

1. 英文期刊：`Smith, J., & Lee, K. (2020). Silicon anodes for lithium-ion batteries: A review. *Nature Energy*, *5*(3), 200-210. https://doi.org/10.1038/s41560-020-0555-5`
2. 中文期刊：`张三, & 李四. (2020). 锂离子电池硅负极研究进展. *储能科学与技术*, *9*(2), 401-410.`
3. 会议论文：`Wang, L., & Chen, H. (2018). Volume expansion of silicon electrodes. In *Proceedings of the National Electrochemistry Conference* (pp. 15-20).`
