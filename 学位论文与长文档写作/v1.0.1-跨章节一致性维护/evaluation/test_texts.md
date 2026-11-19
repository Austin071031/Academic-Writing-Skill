# 测试文本与测试结果（全部合成数据）

> 本文档所有输入文本均为**合成**（synthetic），不来自任何真实论文或评测案例。

## T1 主流程案例（合成）
输入：`../_test/input/`（ch1_intro.md 含"固态电解质（solid-state electrolyte, SSE）/
全固态电池（all-solid-state battery, ASSB）"定义与 [1][2] 引用；ch2_method.md；
facts.md；refs.bib）。注意：_test/input 为多版本共享目录，本测试命令显式只传入
上述 4 个文件，不受目录中其他版本测试文件影响。

步骤：init_result → inspect_case → parse_chapters → scan →（写 glossary_review）→
glossary → impact → assemble_result → validate_output → render_previews。

结果（2026-11-19 最终复跑，_test/work2 + _test/output2）：
- parse_chapters：3 文件 / 2 标题 / 12 段 / 2 引用标记 —— PASS
- scan：术语候选 4 条（固态电解质/全固态电池/交流阻抗谱/两步烧结），dangling 0 —— PASS
- glossary：4 条术语，异写 3 处（SSE、两步烧结法、两步烧结工艺），冲突 0 —— PASS
- impact --changed-term 固态电解质：1 段；--changed-sid C02-S001：3 段 —— PASS
- validate_output：PASS（status=success）；preview.html 生成（3 个产物）—— PASS

## T2 负例（合成：异写混用 + 悬空引用 + 跨章矛盾）
输入：`../_test/work2/neg/ch1.md ch2.md ch3.md`——同一概念混用
"固态电解质 / SSE / solid-state electrolyte / solid state electrolyte"四种写法；
正文引用"图3-1"但全文无图3-1 注；第1章与第3章结论句主语相同、极性相反。

期望与实测：
- dangling = [图3-1 @ C01-S001-P002] —— PASS（检出）
- unreferenced = [图2-1 @ C02-S001-P002] —— PASS
- 异写 = 3 处（SSE / solid-state electrolyte / solid state electrolyte），定义处豁免 —— PASS
- 矛盾候选 = 1 对（C01-S001-P004 正 vs C03-S001-P001 负，overlap 0.45）—— PASS
- impact --changed-sid C02-S001 = 4 段（自身 3 段 + 引用表2-1 的 C01-S001-P002）—— PASS
- impact --changed-term 固态电解质 = 6 段 —— PASS
- 冲突单测：double_definition 与 symbol_clash 各检出 1 例 —— PASS

## T3 反例（合成：写法统一 + 引用有定义）
输入：`../_test/work2/pos/ch1.md ch2.md`——全文统一写"固态电解质"，
图2-1/表2-1 引用与定义一一对应。

期望与实测：dangling 0、unreferenced 0、编号问题 0、异写 0、冲突 0 —— 零误报 PASS

## 工程检查（2026-11-19 实测）
- 全部 9 个脚本 py_compile 通过 —— PASS
- Skill 目录文件数 19（≤50）—— PASS
- 总大小 130,551 字节（≤2 MB）—— PASS
- 符号链接 0 个；__pycache__ 已清理 —— PASS
