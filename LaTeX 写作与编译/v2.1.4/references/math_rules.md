# 公式排版判据（M1-M7）与正误对照

math_audit.py 只诊断；以下判据供 Agent 决定改与不改。原则：**先满足 task.md 的显式
要求，再满足通用排版规范；材料原文的数学含义永远优先于排版偏好。**

## M1 `$$...$$` → `\[...\]`

plain TeX 的 `$$` 绕过 LaTeX 的间距与编号机制（与 fleqn 等类选项不一致）。
误：`$$E=mc^2$$`　正：`\[E=mc^2\]`
注意：跨多行的 `$$` 配对要按出现次序配，改前先数清。

## M2 eqnarray → align

eqnarray 的等号间距错误（`&=&` 产生过宽间隙）且与 amsmath 不兼容。
误：
```tex
\begin{eqnarray} a &=& b + c \\ &=& d \end{eqnarray}
```
正：
```tex
\begin{align} a &= b + c \\ &= d \end{align}
```
迁移要点：`&=&`→`&=`；删去行尾多余 `&`；编号行为一致（每行编号，\notag 抑制）。

## M3 编号与引用一致性

- M3a 带 \label 的公式从未被 \eqref 引用：任务若要求"仅被引用公式编号"，改 * 环境
  或加 \notag；否则保留并记 info。
- M3b \eqref 指向非公式标签（章节/图/表）：疑似串号，核对标签位置后改用 \ref 或
  修正引用键；这是"改得对"的高价值缺陷，必须逐条处置。
- 正文叙述核对：搜索"式 ("、"Eq."、"公式 ("等叙述，确认编号与实际一致。

## M4 斜体文字下标

`x_{max}` 会把 max 排成三个斜体字母连乘。文字含义下标用正体：
`x_{\mathrm{max}}`、`V_{\mathrm{cc}}`；变量下标（`x_i`、`a_{ij}`）保持斜体不改。
判断口诀：下标读起来是一个词（max, eff, in, out）→ 正体；是指标符号 → 斜体。

## M5 单位正体与 siunitx

数学模式中的 `$10 kg$` 会把 kg 排成斜体且数字与单位间距错误。
正：`\qty{10}{\kg}`（siunitx v3）或 `\SI{10}{\kg}`（v2）；文本中 `10 kg` 也应统一
走 siunitx 以锁定字体与间距。复合单位：`\qty{9.8}{\m\per\s\squared}`。
注意：先确认 siunitx 已加载；v2/v3 命令语法差异以编译结果为准。

## M6 裸算子

`$sin(x)$` 排成 s·i·n·(x)。正：`$\sin(x)$`；无预定义的算子：
`\operatorname{rank}(A)`；全文复用的自定义算子应在导言区
`\DeclareMathOperator{\rank}{rank}`（记 change_log）。

## M7 \left / \right 配对

同行数量不等即报；跨行配对：
```tex
\left( a + b \right. \\ \left. + c \right)
```
或放弃自适应改固定尺寸 \Bigl( ... \Bigr)。

## 定理环境（附加）

- 定理类环境须先 `\newtheorem{theorem}{定理}`（amsthm）；引用用 \ref{thm:x}。
- proof 环境来自 amsthm；无 amsthm 时 `\begin{proof}` 报 undefined environment。
- 任务要求"定理按章编号"：`\newtheorem{theorem}{Theorem}[section]`。
