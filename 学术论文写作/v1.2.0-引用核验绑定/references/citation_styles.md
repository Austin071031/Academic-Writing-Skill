# 引用格式模板（按 brief.citation_style 选用，全篇唯一）

## GB/T 7714（顺序编码制，默认）
- 正文：`……催化效率显著提升[1]。`、`……已有报道[2-4]。`
- 文献表：
  - 期刊：`作者1, 作者2, 作者3, 等. 题名[J]. 刊名, 年, 卷(期): 起页-止页. DOI`
  - 会议：`作者. 题名[C]//会议名. 出版地: 出版者, 年: 页码.`
  - 专著：`作者. 书名[M]. 版次. 出版地: 出版者, 年: 页码.`
  - 预印本：`作者. 题名[EB/OL]. (发布日期)[引用日期]. 网址或 arXiv 号.`
- 缺字段处理：材料未给卷期页/DOI 则整段省略，不补造。

## APA 7（著者-出版年）
- 正文：`(Smith & Wang, 2020)`、三作者以上 `(Smith et al., 2020)`、同作者同年 `(2020a, 2020b)`
- 文献表：`Author, A. A., & Author, B. B. (2020). Article title in sentence case. Journal Name, 15(3), 215–223. https://doi.org/xxx`
- 按第一作者字母序排列，不编号。

## IEEE（数字顺序）
- 正文同 GB/T 7714 的 `[1]`。
- 文献表：`A. Author and B. Author, "Article title," Journal Abbrev., vol. 15, no. 3, pp. 215–223, 2020, doi: xxx.`

## Vancouver（数字顺序）
- 文献表：`Author AA, Author BB. Article title. Journal Abbrev. 2020;15(3):215-23. doi: xxx.`

## 统一规则（任何格式）
- 同一篇文献全篇同一编号/同一著录；重复条目合并（保留字段最全者，记 change_log）。
- 中文文献作者写全名，三人以上加", 等"；西文三人以上 ", et al."。
- 文献表内标点统一：中文条目用全角逗号或按 GB/T 7714 半角点号，全篇一致。
