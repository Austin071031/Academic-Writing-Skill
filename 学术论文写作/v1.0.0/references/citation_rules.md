# 引用规则（引得对）

## 1. 引用来源
- 只用 `/app/work/bibliography.json` 中的条目（源自材料中的参考文献列表/原文 PDF）。
- bibliography.json 为空但任务要求引用时：在 uncertainty 中写"材料未提供参考文献列表，无法建立引用"，
  不得虚构文献；任务明确允许外部补充时，只用真实可查条目（作者、年份、期刊/会议、DOI 齐全），
  逐条记入 bibliography 补充段并在 change_log 注明检索来源。

## 2. 论断—引用绑定
- 每条引用必须支撑**它所在的那句**论断，而不是该段的泛泛背景。
- 引用前打开该条目的 `raw` 与 `source` 锚点核对：作者、年份、DOI 与条目一致；条目内容（题名/主题）与论断相关。
- 一条文献只引其真实支持的结论；同一文献不得同时支撑相互矛盾的论断。
- 禁止装饰性引用：与句子论断无直接关系的引用删除；成稿后 check_consistency 会标出"未被正文引用的文献表条目"。

## 3. 格式统一（按 brief.citation_style）
- `gbt7714`（默认，顺序编码制）：正文 `[1]`、`[2-4]`；文献表：
  `作者. 题名[J]. 刊名, 年, 卷(期): 起页-止页. DOI`（材料未给卷期页则省略对应段，不编造）。
- `apa`（著者-出版年）：正文 `(Smith et al., 2021)`；文献表：
  `Author, A. A., & Author, B. B. (2021). Title. Journal, volume(issue), pages. https://doi.org/...`
- `ieee`：正文 `[1]`；文献表：`A. Author and B. Author, "Title," Journal, vol. x, no. y, pp. z-z, Year, doi: ...`
- `numeric`/`vancouver`：同 gbt7714 正文标注；文献表格式按材料原有样式统一。
- 未知/未指定样式：退化为 GB/T 7714 顺序编码制，并在 change_log 说明。

## 4. 文献表条目处理
- 条目字段照抄材料原文；缺 DOI/卷期页的条目保持缺失（check_consistency 仅 WARN，不补假字段）。
- 材料中的条目顺序按正文首次引用顺序重排（顺序编码制要求）；重排记入 change_log。
- 重复条目合并，保留信息最全的一条，合并记入 change_log。

## 5. 引用核验回路（成稿前必做）
1. `check_consistency.py` 的 citations 检查：悬空引用（正文引用了文献表不存在的编号）与冗余条目必须清零；
2. 逐条目人工（Agent）复核 evidence_map 中 type=citation 的行：该引用支撑的论断与条目主题一致；
3. 作者、年份、期刊、DOI 与 bibliography.json `raw` 原文逐字段一致——不一致以材料原文为准改正。
