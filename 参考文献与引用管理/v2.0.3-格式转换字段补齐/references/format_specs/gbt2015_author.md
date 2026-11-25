# GB/T 7714—2015 著者-出版年制 规范数据文件（规范示例整理）

> 数据文件：`scripts/convert_engine.py` 解析下方"机器可读参数"节；正文供 Agent 与人参考。
> 与顺序编码制的差别仅在文内标注（（著者, 出版年））与文献表排序（按著者字顺/语种），条目本体格式一致。

## 机器可读参数（convert_engine 解析，请勿改动键名）

- template: "{authors}. {year}. {title}[{tag}]. {venue}, {volume}({issue}): {pages}."
- label: ""（不编号，文内用 （著者 出版年） 标注）
- max_authors: 3
- zh_truncate_suffix: ", 等"
- en_truncate_suffix: ", et al"
- punct_zh: fullwidth
- punct_en: halfwidth
- western_name_form: "Surname I（姓首字母大写 + 名首字母，不臆造中间名）"
- sort: "中文在前按拼音/笔画，英文在后按字母；同著者按年份"

## 条目模板字符串

期刊：`主要责任者. 年. 题名[J]. 刊名, 卷(期): 起止页码. DOI: xxx.`
会议：`主要责任者. 年. 题名[C]//会议名: 起止页码.`
专著：`主要责任者. 年. 书名[M]. 出版地: 出版社.`

## 作者截断规则

- 同顺序编码制：≤3 全列，>3 取前 3 加 `, 等` / `, et al`。
- 文内标注：1 人 `（张三, 2020）` / `(Smith, 2020)`；2 人 `（张三 和 李四, 2020）` / `(Smith & Lee, 2020)`；3 人以上 `（张三 等, 2020）` / `(Smith et al., 2020)`。

## 标点规则

- 英文条目半角、中文条目全角；DOI 串原样保留。详见 ../punctuation_rules.md。

## 类型标识表

见同目录 `gbt_type_tags.md`（引擎运行时读取，不在脚本硬编码）。

## 示例条目（规范示例，非真实文献）

1. 英文期刊：`Smith J, Lee K. 2020. Silicon anodes for lithium-ion batteries: a review[J]. Nature Energy, 5(3): 200-210. DOI: 10.1038/s41560-020-0555-5.`
2. 中文期刊：`张三, 李四, 王五, 等. 2020. 锂离子电池硅负极研究进展[J]. 储能科学与技术, 9(2): 401-410.`
3. 学位论文：`王五. 2019. 硅基负极材料的制备与性能[D]. 北京: 某大学.`
