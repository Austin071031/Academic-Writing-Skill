# 高频编译错误修复剧本（fix playbook）

每个剧本：症状 → 定位 → 修复 → 验证。所有修复记 change_log（op/file/line/before/after/reason）。

## P1 缺宏包引发的级联（最高频）

- 症状：log_report 显示大量 undefined_control_sequence，root_cause_hypothesis 指向某宏包。
- 定位：`python3 $S/tex_logscan.py --work /app/work --top 10`，看 likely_package。
- 修复：`python3 $S/safe_fix.py --work /app/work`（白名单自动补 \usepackage；
  hyperref/cleveref 自动置于宏包区末尾）。
- 验证：复编 tag=iter1，错误数应断崖式下降；若 likely_package 为空，说明是自定义命令
  拼写错误，到 file:line 人工核对。

## P2 中文/Unicode 成片报错

- 症状：几十上百条 `Unicode character X (U+XXXX)`，category=unicode_char_pdflatex。
- 修复 A（首选）：复编时 `--engine xelatex`（tex_build auto 模式已自动识别 CJK）；
  safe_fix 会在主文件首行加 `% !TEX program = xelatex` 便于复现方选对引擎。
- 修复 B（任务要求必须用 pdflatex 时）：导言区补 `\usepackage[utf8]{inputenc}`
  `\usepackage[T1]{fontenc}`；中文则换 `\usepackage{ctex}`（ctex 会自动处理，
  但 pdflatex+ctex 字体受限，须在 uncertainty 说明取舍）。
- 红线：不得把中文内容删掉或改成拼音来"修编译"。

## P3 交叉引用不收敛（converged=false）

- 症状：多轮编译后日志仍有 `Rerun to get cross-references right` 或 undefined reference。
- 排查顺序：
  1. `python3 $S/tex_check.py --work /app/work` 看 undefined_refs —— 真缺 \label 就补；
     键名笔误（fig: vs figu:）统一为材料中占优的命名风格；
  2. duplicate_labels —— 同名 \label 多处，保留正确一处；
  3. 若 ref 指向材料中不存在的对象（如图 5 但全文只有 3 图）：记 manual_confirmations，
     不得虚构图；任务允许时把引用改为文字描述并记 change_log。
- 验证：复编后 needs_rerun 消失、source_check.undefined_refs=0。

## P4 bibtex/biber 链路

- 症状：Citation undefined 成片，或参考文献列表为空。
- 排查：build_report.passes 中是否有 bib 工具一轮；没有说明主文件无 \bibliography
  或 tex_build --bib 识别失败 → 显式 `--bib bibtex`（或 biber）重跑。
- 条目缺失：tex_check.undefined_cites 给键清单；在 .bib 中搜近似键（大小写/年份差异）
  修正正文键名；确无条目且材料（如论文 PDF 的参考文献表）提供信息时，按材料补条目
  （作者/题名/年份/出处以材料为准），记 change_log；材料不提供则记 manual_confirmations。
- 红线：不编造 DOI、卷期页；查不到就不写该字段，宁缺勿假。

## P5 表格列数不匹配（Extra alignment tab）

- 症状：category=table_column_mismatch，定位行在 tabular 内。
- 修复：数该行 & 数 vs 列声明（l/c/r/p 个数）；多 & 删、少 & 补；
  含 \multicolumn{n} 时按 n 列计。改完复编。
- 进阶：任务要求三线表时，hline 模式可用 v3 方向思路机械转换（本版手工执行：
  首行 \hline→\toprule、表头后 \hline→\midrule、末行 \hline→\bottomrule，
  删竖线 |），并确认加载 booktabs。

## P6 括号/环境失控（Runaway argument）

- 症状：runaway_argument 后跟随大量 emergency_stop。
- 定位：从 file:line 向上找最近的未配对 {；tex_check.env_imbalance 给出
  \begin/\end 不配平的环境清单。
- 修复：补缺的那一半；切勿为消错把整段注释掉（内容丢失须记 uncertainty 才算合规）。

## P7 编译超时/挂起

- 症状：build_report.passes 中 timed_out=true。
- 排查：\input 自包含（A \input A）、未闭合的环境嵌套、超大循环宏；
  用 tex_check.env_imbalance 与 inspection.inputs 辅助。
- 处置：修复后复编；无法定位时记 exceptions，status≤partial。

## Worked example（合成示例，非正式案例）

工程 main.tex 使用 \toprule 但未加载 booktabs，正文含中文，缺 \input{chap2}：
1. baseline：pdflatex 报 47 条 Unicode 错误（根因：引擎错配）。
2. 换 xelatex 复编：剩 3 条 undefined_control_sequence（\toprule × 3，级联自缺 booktabs）
   + 1 条 missing_file（chap2.tex）。
3. safe_fix：补 \usepackage{booktabs} + 建 chap2.tex 占位（登记 manual_confirmations）。
4. final 复编：0 错误，success=true；chap2 内容缺失记入 uncertainty，status=partial
   （因占位内容待人工补写）。全过程 change_log 4 条、fix_log 3 条，均可回溯到日志行。
