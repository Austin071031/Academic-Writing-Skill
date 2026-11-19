# 合成测试文本（标注：全部为合成数据，仅供功能验证）

## 源文 T1（含缩写展开、化学式、中文异写）
"本研究采用硫化物固态电解质（SSE）与 LiNi0.8Co0.1Mn0.1O2（NCM811）正极构建全固态电池。
SSE 的离子电导率达 12 mS/cm，但固体电解质与正极之间的界面副反应限制了循环寿命。
通过原子层沉积（ALD）在 NCM811 表面包覆 5 nm 的 LiNbO3 缓冲层。……"
预期：candidates 检出 T001（canonical=硫化物固态电解质，variants 含 SSE/固体电解质/固态电解质）、
NCM811↔化学式配对、ALD↔原子层沉积配对；单位 mS/cm 不成条目。

## 正例改写稿 T2（统一说法+首次展开）
"……核心部件之一是硫化物固态电解质（SSE）——一种用固体传导锂离子的电解质。SSE 的离子电导率
高达 12 mS/cm……研究团队用原子层沉积（ALD）技术包覆 5 nm 厚的 LiNbO3（铌酸锂）缓冲层……"
预期：audit PASS（0 critical / 0 warn），exit=0。

## 反例改写稿 T3（同一概念两种说法 + 缩写未展开）
"固态电解质被视为下一代电池的关键材料。研究团队发现，SSE 与 NCM811 正极之间存在界面副反应……
通过 ALD 技术包覆后，固体电解质的界面阻抗由 320 Ω 降至 45 Ω……"
预期：variant_used warn ×2（固态电解质、固体电解质）+ acronym_not_expanded critical ×2（SSE、ALD），exit=2。

## 反例第二产物 T4（跨产物不一致）
简报中主导说法改为"固体电解质"（改写稿用"硫化物固态电解质/SSE"）：
预期 cross_file_inconsistent warn（+variant_used warn）。

## 反例 T5（一缩写两展开）
同稿先写"固体电解质（SSE）"后写"硫化物固态电解质（SSE）"：
预期 symbol_conflict critical。

## 边界 T6（表外新说法）
稿中出现"硫化物固态电解液"（未登记，与 canonical 相似度≈0.88）：
预期 unlocked_change warn。
