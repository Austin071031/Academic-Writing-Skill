# GB/T 7714—2015 顺序编码制 规范数据文件（规范示例整理）

> 数据文件：`scripts/convert_engine.py` 解析下方"机器可读参数"节；正文供 Agent 与人参考。

## 机器可读参数（convert_engine 解析，请勿改动键名）

- template: "{authors}. {title}[{tag}]. {venue}, {year}, {volume}({issue}): {pages}."
- label: "[n] "
- max_authors: 3
- zh_truncate_suffix: ", 等"
- en_truncate_suffix: ", et al"
- punct_zh: fullwidth
- punct_en: halfwidth
- western_name_form: "Surname I（姓首字母大写 + 名首字母，不臆造中间名）"
- doi_form: "DOI: {doi}."

## 条目模板字符串

期刊：`主要责任者. 题名[J]. 刊名, 年, 卷(期): 起止页码. DOI: xxx.`
会议：`主要责任者. 题名[C]//会议名. 年: 起止页码.`
专著：`主要责任者. 书名[M]. 出版地: 出版社, 年.`

## 作者截断规则

- 3 人以内全列；超过 3 人取前 3 人，中文条目后加 `, 等`，英文条目后加 `, et al`。
- 西文姓名：`Smith, John` → `Smith J`（仅姓 + 名首字母，**不得臆造中间名**）。
- 中文姓名照录，不缩写。

## 标点规则

- 英文条目内逗号、句号、冒号一律半角并后跟空格。
- 中文条目一律全角（，．：（）），DOI 串保持原样不改写。详见 ../punctuation_rules.md。

## 类型标识表

见同目录 `gbt_type_tags.md`（引擎运行时读取，不在脚本硬编码）。

## 示例条目（规范示例，非真实文献）

1. 英文期刊：`[1] Smith J, Lee K. Silicon anodes for lithium-ion batteries: a review[J]. Nature Energy, 2020, 5(3): 200-210. DOI: 10.1038/s41560-020-0555-5.`
2. 中文期刊（4 作者截断）：`[2] 张三, 李四, 王五, 等. 锂离子电池硅负极研究进展[J]. 储能科学与技术, 2020, 9(2): 401-410.`
3. 会议论文：`[3] Wang L, Chen H. Volume expansion of silicon electrodes[C]//Proceedings of the Electrochemical Society Meeting. 2018: 15-20.`
