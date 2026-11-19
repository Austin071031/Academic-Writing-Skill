# 已知失败模式与规避（表格方向）

| 失败模式 | 表现 | 规避 |
|-|-|-|
| resizebox 万能 | 所有宽表都 \resizebox{\textwidth}{!}{...} | 这是 finding 不是解药；按 table_rules T5 分流 |
| 字号连降 | \small → \footnotesize → \scriptsize 层层缩水 | 最多一档且记 change_log；再宽就改结构 |
| booktabs 半吊子 | 换了 \toprule 但留竖线和 \hline | 三线表=去竖线+只留三条主横线（复合表头用 \cmidrule） |
| 改数据凑对齐 | 为列数一致删了一个数据列 | 数据不可动；结构问题只改结构 |
| label 放 caption 前 | \ref 拿到章节号 | label 永远紧跟 caption 之后 |
| longtable 进浮动体 | longtable 外包 table 环境报错 | longtable 自带题注机制，不进 table 环境 |
| 启发式当实锤 | 按 T7 字符数直接重排一个并不宽的表 | 先目视 PDF 确认；误报记 uncertainty |
| 机械转换复杂表 | \cline 混排表被 apply-booktabs 改坏 | 脚本只转简单模式；复杂表手工改造 |
| 浮动体消失 | [H] 强制定位导致图表顺序错乱 | 放宽 [htbp] 让 LaTeX 调度；必要时 \clearpage |
| 题注模板冲突 | 期刊模板 caption 格式被 caption 宏包覆盖 | 模板自带题注机制时不加载 caption 宏包，记 uncertainty |
