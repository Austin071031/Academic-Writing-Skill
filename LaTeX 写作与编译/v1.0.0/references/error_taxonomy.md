# LaTeX 编译错误分类体系（tex_logscan.py 的 category 与首选修法）

| category | 典型日志信息 | 根因 | 首选修法 |
|-|-|-|-|
| missing_file | `File 'xxx.sty' not found` / `File 'xxx.cls' not found` | 宏包/类未安装，或模板自带文件未随工程提供 | 查材料目录是否自带 .sty/.cls；有则确认路径；没有则换功能等价宏包（记 change_log）；类文件缺失且无替代时用通用类兜底（记 uncertainty） |
| missing_file(input) | `File 'chap1.tex' not found` | \input/\include 目标缺失 | safe_fix 建 TODO 占位 + manual_confirmations；材料中有该内容则补写 |
| missing_file(graphics) | `File 'fig1.pdf' not found` | 图片缺失 | 保留引用，记 manual_confirmations；不删图引用凑编译 |
| undefined_control_sequence | `Undefined control sequence. \toprule` | 宏包未加载或命令拼写错误 | likely_package 白名单补 \usepackage；拼写错误按上下文改命令名 |
| unicode_char_pdflatex | `Unicode character 测 (U+6D4B) not set up for use with LaTeX` | CJK/Unicode 内容 + pdflatex | 成片出现时换 xelatex/lualatex 编译（不必改源码）；零星出现可换等价命令（---、$\times$ 等） |
| math_mode | `Missing $ inserted` | 数学符号出现在文本模式 | 到 file:line 给数学片段补 $...$ 或 \(...\) |
| runaway_argument | `Runaway argument? Paragraph ended before ...` | 大括号未闭合/参数跨段 | 从 file:line 向上找未闭合的 {；修复配平 |
| brace_mismatch | `Extra }, or forgotten }` / `Missing }` | 大括号配平错误 | tex_check 的 env_imbalance 辅助定位；逐行核对 |
| undefined_reference | `Reference 'fig:x' on page N undefined` | \label 缺失或键名不一致 | tex_check.undefined_refs 定位；补 \label 或改键名；标签在材料中本无对应对象时记 manual_confirmations |
| undefined_citation | `Citation 'key' on page N undefined` | bib 缺条目/键名笔误/未跑 bibtex | 先确认 bib 工具已运行；再近似键比对；缺条目按材料补全 |
| multiply_defined | `Label 'eq:x' multiply defined` | 同一 \label 出现多次 | tex_check.duplicate_labels 定位；保留一处并同步引用 |
| option_clash | `Option clash for package xxx` | 同一宏包以不同选项重复加载 | 合并为一次加载，选项取并集（注意兼容性） |
| font_missing | `Font ... not found` | 字体未安装（xelatex/lualatex 下常见） | 换材料允许的等价字体；记 uncertainty |
| table_column_mismatch | `Extra alignment tab has been changed to \cr` | 行内 & 数多于列声明 | v3 方向 table_audit 的 T3 可自动定位；v1 手工到 file:line 核对 |
| table_rule_misplaced | `Misplaced \noalign` | \hline 位置错误（如不在行首） | 把 \hline/\toprule 移到 \\ 之后新行开头 |
| dimension_error | `Missing number, treated as zero` / `Illegal unit of measure` | 长度参数缺数字/单位 | 到 file:line 补正确长度（如 0.8\textwidth） |
| emergency_stop | `Emergency stop` | 前序错误导致的终止 | 修第一个错误后复编，此项通常消失（级联） |
| capacity_exceeded | `TeX capacity exceeded` | 死循环（如 \input 自包含、未闭合环境递归） | 查 \input 环、环境配平；定位后修复 |
| missing_begin_document | `Missing \begin{document}` | 导言区出现正文内容/缺 \begin{document} | 检查 \begin{document} 是否存在；导言区混入的正文移回 |
| rerun_needed（警告） | `Rerun to get cross-references right` | 交叉引用未收敛 | tex_build --until-converge 会自动多轮；仍不收敛查 undefined_reference |

## 级联判读原则

1. 只有**第一条错误**是可信的根因候选；其后错误若 category 属于
   undefined_control_sequence/undefined_environment/math_mode/other，大概率为级联。
2. 典型级联链：缺 booktabs → \toprule 未定义 → tabular 结构崩溃 → 几十条
   `Misplaced \cr`/`Missing $`。修一处 `\usepackage{booktabs}` 全消。
3. 修完根因必须**立即复编**确认级联消除，再处理下一批非级联错误。
