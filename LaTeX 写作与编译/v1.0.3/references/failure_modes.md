# 已知失败模式与规避（引用方向）

| 失败模式 | 表现 | 规避 |
|-|-|-|
| 删引用凑收敛 | 把悬空的 \cite 句子删掉 | 引用是内容；缺条目记 manual_confirmations，禁止删文 |
| 编造 DOI/页码 | 补条目时填查不到的字段 | 字段以材料为唯一来源；留空优于造假 |
| 误并不同文献 | 标题相近的两篇被合一 | 合并判据三条满足两条；拿不准不合并记 uncertainty |
| 静默去重 | 删了条目没记录 | change_log 必须有 keep/drop/rationale 与正文键名映射 |
| bib 轮缺失 | 参考文献表空，反复改正文键名 | 先看 build_report.passes 有没有 bib 工具轮 |
| bcf 版本错配 | biber 与 biblatex 版本不匹配报错 | 改 backend=bibtex 或对齐版本，记 change_log |
| 样式混排 | 一部分 [1] 一部分 (Smith, 2020) | natbib 选项统一；按 task.md/模板执行 |
| 键名大改写错 | bib 键大小写敏感，改成不存在的大小写 | 近似比对以 bib 实际键为准 |
| 多 bib 文件遗漏 | 只扫了一个 .bib | cite_audit 遍历工程全部 .bib；相信报告而非印象 |
| 收敛假象 | 只看 success 不看 converged | 两者分开报告；不收敛项逐条登记 |
