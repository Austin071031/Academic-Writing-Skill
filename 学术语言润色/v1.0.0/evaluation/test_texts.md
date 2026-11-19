# 合成测试文本（标注：以下文本均为合成的测试用例，非真实论文内容）

用于回归测试 Skill 的识别与守恒能力。每段标注"埋入的问题"与"期望行为"。

## T1 中文期刊摘要（埋入：人称、口语化、冗余、绝对化）

> 我们做了一个新的实验来测试这个材料的性能，结果非常的好。实验结果表明，材料的强度
> 提高了50%左右，这证明我们的方法是最好的。但是成本高的问题还没有解决，这个问题
> 很值得关注。该方法可能用于航空航天领域。

期望：去人称与口语化（"做了/非常的好/最好的"）；保留"左右/可能"（限定守恒）；
"这证明我们的方法是最好的"若无证据支撑应降级并在 reason 说明或存疑保留。

## T2 英文引言（埋入：悬垂、时态、冠词、宣传词、引用）

> As shown in previous works, the catalyst exhibit high activity. We developed a novel
> and unique method which is very excellent. The conversion rate reached 98.2% [3], that
> is higher than reported values [4,5]. Our results proves the mechanism proposed by
> Smith et al. (2021).

期望：exhibit→exhibits；a accuracy 类冠词无误但 *the catalyst exhibit* 为主谓一致；
*novel and unique* 去宣传词；*that* 从句改 *which*；proves→suggest/indicate（证据强度守恒）；
引用 [3]、[4,5]、(2021) 全部原样。

## T3 中英混排基金本（埋入：直译腔、逻辑连接词滥用、因果误用）

> 本项目将发展一种高通量筛选方法。Moreover，通过机器学习和实验验证的结合，
> 我们有望快速发现高性能催化剂。由于该方法效率高，因此它将导致材料研发模式的变革。
> 相关研究表明，催化剂的活性与其电子结构密切相关[7,8]。

期望：Moreover 位置与密度调整；"由于…因此…"删一个；**"导致"是因果表述，若原文保持因果
则不改，但"密切相关"不得升级为因果**；"有望"保留。

## T4 守恒陷阱（任何改动都应触发 guard critical）

> 初步结果表明，该关联可能部分源于界面效应（约12%），但并非所有样本均表现出
> 该趋势（p = 0.03，见图3）。已有研究指出，类似现象与缺陷浓度相关 [9]。

期望行为：对 modify 任何句子，若改文出现以下任一情况必须被 guard_check 拦截：
删"初步/可能/约/部分/并非"；12% 数值变动；p = 0.03 变动；图3 指向变动；
"相关"改"导致"。

## T5 LaTeX 片段（埋入：语法、弱动词）

> The results of the calculation shows that the band gap is $1.45\,\mathrm{eV}$, which
> is in agreement with the experimental value of 1.4 eV~\cite{liu2022}. We made an
> analysis of the density of states (see Fig.~\ref{fig:dos}). The error are less than
> 2\% for all structures.

期望：shows 主谓一致；*made an analysis of* → *analyzed*；$1.45\,\mathrm{eV}$、
\cite{liu2022}、Fig.~\ref{fig:dos}、2\% 全部原样（含 LaTeX 命令与空格）。
