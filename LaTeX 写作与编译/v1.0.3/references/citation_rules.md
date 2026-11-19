# 引用与参考文献判据（C1-C6）

## C1 悬空 \cite 键（error）

正文 \cite{key} 在任何 .bib 中都找不到。处置优先级：
1. 键名笔误：与现有 bib 键做近似比对——同一作者姓氏 + 相同/相邻年份 + 键形相似
   （编辑距离小），三项满足两项才算高置信，改正文键名并记 change_log。
2. 条目真缺：材料（论文 PDF 参考文献表/任务数据）有该文献信息 → 按材料补条目，
   记 change_log（evidence 指向材料位置）；材料没有 → 记 manual_confirmations，
   引用原样保留。
3. 禁止：为消错删除引用语句；禁止编造条目。

## C2 未被引用条目（info）

按任务要求：要求"只列被引文献"→ 移除并记 change_log；要求"保留全部"→ 保持或
\nocite{key}；任务未说明 → 保持现状并记 info，不擅动。

## C3 疑似重复条目（warn，合并判据）

脚本按规范化标题相似度 ≥0.90 给出候选对。人工合并判据（满足两条才合并）：
- 规范化标题相似度 ≥0.90；
- 第一作者姓氏一致；
- 年份相同或相差 ≤1（预印本→正式版跨年常见）；
- 典型场景：arXiv 预印本 vs 期刊正式版（保留正式版）、中英文题名重复收录
  （按目标语言保留）、不同数据库导出字段差异。
合并动作：保留字段更全者；正文 \cite 统一为保留键；change_log 记 keep/drop/rationale。
反例（不得合并）：同标题会议的不同届次、同一作者同年不同工作（标题相似但不同文）。

## C4 关键字段缺失（warn）

- 所有条目：author、year、title 必备；
- @article：journal 必备；@inproceedings：booktitle 必备；
- 补全来源仅限材料；补不到留空记 uncertainty。DOI 有则保留，无则不强求
  （stats 报告 DOI 覆盖率供任务参考）。

## C5 样式机制冲突（error/warn）

| 情形 | 判定 | 处置 |
|-|-|-|
| \citep/\citet 但未加载 natbib/biblatex | error | 补 \usepackage{natbib}（或按模板） |
| biblatex 与 \bibliographystyle 并存 | warn | biblatex 不认 \bibliographystyle；按模板二选一 |
| \bibliographystyle 指定的 .bst 不存在 | error | 换可用样式并记 uncertainty（著录格式可能不保真） |
| 数字/作者-年份混用 | warn | 全文统一，按 task.md/模板；natbib 选项 numbers/authoryear |

## C6 重复 bib key（error）

同一键两条条目：bibtex 只取第一条，行为不可预期。合并保留信息全者，记 change_log。

## bibtex / biber 链路

- \bibliographystyle + \bibliography → bibtex 链路；\usepackage[...]{biblatex} +
  \addbibresource → biber 链路（backend=bibtex 时例外）。
- tex_build 自动识别并插入 bib 工具轮；识别失败时显式 `--bib bibtex|biber`。
- 链路验证三信号：.bbl 生成、日志无 "Citation undefined"、PDF 末页有参考文献表。
- 多轮收敛：改任何引用后需 engine→bib→engine→engine；--converge 自动执行并
  以日志无 Rerun 提示为收敛判据（上限 4 轮）。
