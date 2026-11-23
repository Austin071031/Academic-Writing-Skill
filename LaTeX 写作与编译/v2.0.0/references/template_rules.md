# 模板适配判据（P1-P5）与迁移范式

## P1 常见文档类必填项（template_audit 内置）

| 类 | 必填项 |
|-|-|
| IEEEtran | \title、\author、abstract 环境、IEEEkeywords（或 \keywords）、\maketitle |
| elsarticle | \title、\author、\affiliation/\address、abstract 环境、keyword 环境、\maketitle |
| acmart | \title、\author、\affiliation、\email、abstract 环境、\keywords、CCS（\ccsdesc/CCSXML）、\maketitle |
| article/ctexart/report/book | \title、\author、\maketitle |
| 未识别类 | 按模板示例 .tex 的注释与结构核对（P1i 提示） |

回填原则：内容只从稿件原文取；原文没有的建 TODO 占位 + manual_confirmations。

## P2 宏包冲突对（内置五组 + 引擎规则）

- natbib × biblatex（互斥，按模板二选一）；
- subfigure × subcaption（弃 subfigure）；
- times × newtxtext（字体方案叠加）；
- babel × polyglossia（xelatex 走 polyglossia/ctex）；
- algorithm2e × algorithmicx（算法体系二选一）；
- xelatex/lualatex 下 inputenc 无效应移除；中文模板优先 ctex 体系。

## P3 加载顺序

- hyperref 最后加载；唯一例外 cleveref 必须在 hyperref 之后；
- 判据：hyperref 之后还有非 cleveref 宏包 → warn；cleveref 在 hyperref 前 → error。

## P4 过时项

epsfig/psfig→graphicx；subfigure→subcaption；times→newtxtext/newtxmath；
`{\bf ...}`/`{\it ...}` 声明式 → `\textbf{...}`/`\textit{...}`。

## P5 与模板差异

- 模板示例加载而稿件缺失的宏包：按需补载（判断是否真用到，不盲目全量复制）；
- 模板规定的 \bibliographystyle：强制对齐；
- 模板的结构机制（IEEEkeywords、keyword 环境、CCSXML）：按类映射改写，
  不可把 article 式 \keywords 直接带进对结构有要求的类。

## 迁移范式（article → 期刊类）

1. 换 \documentclass（选项按任务/模板示例）；
2. 元数据回填到模板命令（作者块差异最大：IEEEtran 的 \IEEEauthorblockN、
   elsarticle 的 \author[aff]{name}、acmart 的 \affiliation+\email）；
3. 摘要/关键词迁入模板环境；
4. 删除模板示例的 dummy 内容（记 change_log）；
5. 图表/公式/参考文献机制按模板调整（双栏类的 table* 跨栏、模板指定 .bst）；
6. 复编译收敛后目视 PDF 首页（作者块/摘要/版式是迁移错误集中区）。

## 可复现清单字段（build_manifest 生成）

引擎与工具版本（真实 --version 首行）、日志中的宏包/类版本、全部源码 sha256、
精确命令序列（含 bib 工具轮）、轮次与收敛状态、OS/Python。
复现注意：同一 TeX Live 年度版本 + 相同命令序列 ⇒ 一致 PDF；宏包版本差异导致的
分页差异属可解释差异。
