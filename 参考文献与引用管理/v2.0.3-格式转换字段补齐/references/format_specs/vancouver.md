# Vancouver（温哥华/ICMJE）规范数据文件（规范示例整理）

> 数据文件：`scripts/convert_engine.py` 解析下方"机器可读参数"节；正文供 Agent 与人参考。
> IEEE 数字制的文内标注与编号方式与本规范兼容（[n] 按出现顺序编号），条目模板略有差异，
> 本文件以 ICMJE/NLM 样式为准。

## 机器可读参数（convert_engine 解析，请勿改动键名）

- template: "{authors}. {title}. {venue}. {year};{volume}({issue}):{pages}. doi:{doi}"
- label: "[n] "（或"n." 依期刊；本引擎用 [n]）
- max_authors: 6（超过 6 人取前 6 + et al.；本引擎按共享内核取前 3 + et al，偏严不丢作者信息于审计）
- zh_truncate_suffix: ", et al"
- en_truncate_suffix: ", et al"
- punct_zh: halfwidth（Vancouver 条目内部一律半角）
- punct_en: halfwidth
- western_name_form: "Surname I（姓 + 名首字母连写无点，如 Smith J）"
- doi_form: "doi:{doi}"

## 条目模板字符串

期刊：`Author AA, Author BB. Title of article. Abbrev Journal Name. Year;volume(issue):pages. doi:xxx`
会议：`Author AA. Title. In: Proceedings Name; Year; Place. p. xx-xx.`
专著：`Author AA. Book title. Place: Publisher; Year.`

## 作者截断规则

- ICMJE：≤6 人全列；>6 人列前 6 人后接 `et al.`（本引擎共享内核按 ≤3 + `et al` 处理，属更严格截断，审计中保留完整作者名单于 library.json）。
- 西文姓名：`Smith, John` → `Smith J`（名首字母不加句点，不臆造中间名）。
- 刊名应使用 NLM 缩写；材料只给全称时**照录全称，不臆造缩写**。

## 标点规则

- 全部半角；卷期页紧凑：`年;卷(期):页.`。
- 中文条目保持中文题名/刊名，结构标点半角；DOI 写 `doi:10.xxxx/...` 原样保留。

## 类型标识表

Vancouver 不使用 `[J]/[C]` 字母标识；电子资源以 `[Internet]` 与引用日期标注，材料未提供时不臆造。

## 示例条目（规范示例，非真实文献）

1. 英文期刊：`[1] Smith J, Lee K. Silicon anodes for lithium-ion batteries: a review. Nat Energy. 2020;5(3):200-10. doi:10.1038/s41560-020-0555-5`
2. 中文期刊：`[2] 张三, 李四, 王五, et al. 锂离子电池硅负极研究进展. 储能科学与技术. 2020;9(2):401-10.`
3. 会议论文：`[3] Wang L, Chen H. Volume expansion of silicon electrodes. In: Proceedings of the National Electrochemistry Conference; 2018; p. 15-20.`
