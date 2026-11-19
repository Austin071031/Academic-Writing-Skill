# 合成测试文本（标注：全部为合成数据，仅供功能验证）

## 正例 T1（论文摘要 → 新闻通稿，台账应 PASS）

源文（合成）：
"原子层沉积界面工程提升全固态电池循环稳定性

近年来，全固态电池因高安全性被认为是下一代储能技术的重要方向。然而，硫化物电解质与高镍正极之间的界面副反应严重制约其循环寿命。

本研究通过原子层沉积（ALD）在正极表面包覆 5 nm 的 LiNbO3 缓冲层，抑制界面副反应。

循环测试表明，包覆后电池在 0.5C 下循环 500 次容量保持率达 85.3%，而未包覆对照组仅为 62.1%（图 2）。

XPS 分析显示 LiNbO3 层抑制了界面处 S 物种的氧化分解，初步表明该策略具有普适性。

该工作为全固态电池界面设计提供了新思路，有望推动产业化进程。相关成果发表于《先进能源材料》。"

改写稿：6-7 段新闻通稿（标题/导语/背景/核心成果/数据/引语占位/展望），
change_reasons.jsonl 每段一条理由，引语占位段标「新增-过渡」。
预期：map 识别 genre=新闻通稿、「引语」「联系方式占位」缺失标注「源文未提供」；
ledger verdict=PASS、exit=0；源文 6 段全覆盖。

## 反例 T2（漏写删除理由 → critical）

同 T1 源文，但改写稿删去含对照数据的段落（85.3%/62.1%/500 次/图 2 所在段），
且 change_reasons.jsonl 不写「删除」理由。
预期：ledger 判 `dropped_without_reason` critical（涉及事实 ≥4 处），verdict=FAIL，exit=2；
修复方式：补 {"source_pid":"...","action":"删除","reason":"..."} 或恢复内容后重跑 exit=0。

## 反例 T3（新增段落未标「新增-过渡」→ warn）

同 T1，但改写稿加入一段"该成果达到国际领先水平，效率提升 30%"（源文外内容），
change_reasons.jsonl 中该段理由缺失或动作写「改写」。
预期：ledger 判 `added_without_reason`/`added_action_mismatch` warn +
`added_contains_number` warn（含"30%"数值）；verdict 仍为 PASS（无 critical）但必须逐条处置。

## 边界 T4（文体未识别 → 默认模板 + manual_confirmations）

task.md 不写目标文体。
预期：map 输出 genre=科普文章、genre_recognized=false，
manual_confirmations 记录"按默认科普文章处理，请人工确认"。
