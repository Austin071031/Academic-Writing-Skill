# 基础 Agent 常见失败模式与本 Skill 对策

1. **缩写不展开**：直接把论文缩写（SSE、ALD）搬进科普稿，公众读者看不懂。
   对策：术语表 first_expand 标记 + audit 查 acronym_not_expanded = critical，未展开不过闸。
2. **同概念多种说法**：同一篇稿里"固态电解质/固体电解质/硫化物固态电解质"混用，读者误以为三个东西。
   对策：机选异写聚类（相似度≥0.70）入 variants，audit 查 variant_used = warn 并给出统一建议。
3. **一缩写两展开**：前段写"固体电解质（SSE）"后段写"硫化物固态电解质（SSE）"。
   对策：audit 全文扫描两种展开写法，symbol_conflict = critical（后缀包含视为同一展开，防误报）。
4. **跨产物口径漂移**：科普稿用"硫化物固态电解质"，简报里又写"固体电解质"。
   对策：audit `--more` 多产物联审，按各产物主导说法比对，cross_file_inconsistent = warn。
5. **改写时顺手"造词"**：为求生动写出表外新说法（如"硫化物固态电解液"），与全文口径冲突。
   对策：unlocked_change 检测与 canonical 相似度≥0.70 的未登记说法，提示改表或改用 canonical。
6. **猜测缩写全称**：源文只写"XPS"未给全称，基础 Agent 常会编一个全称。
   对策：红线禁止臆造全称；用描述性说法替换 + manual_confirmations 待作者确认。
7. **逐处手改口径**：发现不一致后逐句手动替换，漏改且无法复核。
   对策：红线要求术语统一必须走 term_table.json 改表后重跑 audit，留 change_log 台账。
8. **化学式写法漂移**：LiNbO3 / Li NbO3 / linbo3 混写。
   对策：拉丁 token 归一化归并（大小写/连字符/空格变体同键），symbol 类条目全文锁定一种写法。
