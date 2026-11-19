# 表格与浮动体判据（T1-T8）与改造范式

## T1/T2 题注与标签

- 每个 table 环境应有 \caption 与 \label{tab:...}；label 置于 caption 之后（否则
  \ref 拿到的是章节号）。
- 题注位置：多数期刊模板要求**表题在表上方、图题在图下方**；以 task.md/模板为准统一。
- 无 caption 的"裸 tabular"若是正文内嵌小表可豁免（记 info）；成浮动体必须补。

## T3 行列数不一致（error 级）

列声明 `lcc` = 3 列；每行 & 数 + 1 + \multicolumn 展开 - 1 应等于 3。
常见根因：合并单元格后忘删 & 、从 Excel 粘贴多空列、\\ 前多 & 。
`Extra alignment tab has been changed to \cr` 即此错在日志中的形态。

## T4 三线表（booktabs）

```tex
% 误：竖线 + 全横线          正：booktabs 三线表
\begin{tabular}{|l|c|}        \begin{tabular}{lc}
\hline                        \toprule
项目 & 值 \\ \hline           项目 & 值 \\ \midrule
甲 & 1 \\ \hline              甲 & 1 \\ \bottomrule
\end{tabular}                 \end{tabular}
```
- 复合表头：`\cmidrule(lr){2-3}` 替代 \cline；左右修剪 (lr) 更美观。
- 表内不再用竖线；需要分列感时用 `@{\hspace{1em}}` 或增加列间距。

## T5 超宽表分流（禁止缩放掩盖）

按根因选方案：
1. 单元格文字长 → **tabularx**：`\begin{tabularx}{\textwidth}{lX}`，X 列自动换行。
2. 列数过多 → 减列（并次要列入注）、转置、或拆成两表。
3. 行多跨页 → **longtable**：`\begin{longtable}{lc} ... \endfirsthead
   \caption[]{续表}\\\toprule...\endhead`；longtable 不进 table 浮动体。
4. 整表超宽且不可拆 → sidewaystable（rotating 宏包，整页横排），须模板允许。
5. 字号只允许降一档（\small 或 \footnotesize）且记 change_log；禁止 \scriptsize 以下。

## T6 浮动位置

- `[h]` 过强、`[H]` 需 float 宏包且禁浮动：统一放宽为 `[htbp]`；
  浮动体堆积（Too many unprocessed floats）时在合适处加 \clearpage。
- 图表应"先文后表"：首次 \ref 出现之后再放浮动体源码（排版上 LaTeX 自动找位置）。

## T7/T8 启发式估计的核实

table_audit 的 T7（>110 字符）/T8（>45 行）是启发式嫌疑，**必须目视 preview.pdf 对应页
确认**再动手；确认无溢出记 uncertainty 说明"启发式报警经目视排除"。

## 数值一致性

表内数值以材料为准；与正文叙述矛盾时以材料原文为准修正并记 change_log
（evidence 指向材料位置）；单位统一在表头声明（如"单位：mm"），表内不再重复单位。
