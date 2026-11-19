# 合成测试文本（标注：全部为合成数据，仅供功能验证）

## 正例源文 T1（硫化物固态电解质论文片段）
"循环测试表明，包覆后电池在 0.5C 下循环 500 次容量保持率达 85.3%，而未包覆对照组仅为 62.1%。
界面阻抗由 320 Ω 降至 85 Ω，降低了 73.4%。XPS 分析显示 LiNbO3 层抑制了界面处 S 物种的氧化分解。
相关结果见图2与表1。2023 年报道的同类策略容量保持率约为 78%。"
预期：facts 检出 85.3%、62.1%、73.4%、78%（percent），320 Ω、85 Ω（number），图2/表1（figure/table_ref），表明/显示（conclusion）；0.5C、LiNi0.8、2023 被遮蔽。

## 正例改写稿 T2（等价改写）
"包覆后的电池循环 500 次后容量保持率达到 85.3%，没包覆的只有 62.1%。界面阻抗从 320 欧姆降到 85 欧姆，下降了 73.4%。相关结果见图2与表1。2023 年报道的同类策略约为 78%。"
预期：check PASS，verbatim 全中，exit=0。

## 反例改写稿 T3（篡改 + 源外新事实）
"包覆后的电池容量保持率达到 89%，能量密度提升 40%。"
预期：源文是 85.3% 改写写成 89% → 判 **altered**（critical）+ `89%` 判 **unverified**（critical）；`40%` 源外 → **unverified**（critical）。exit=2。

## 反例改写稿 T4（图表编号臆造）
"相关结果见图3。"
预期：figure_ref_unknown critical（源文只有图2/表1）。exit=2。

## 正例换算稿 T5（derived）
"缓冲层厚 0.005 μm，容量保持率 0.853，阻抗从 320 Ω 降至 0.085 kΩ，降幅约 73%。相关结果见图2与表1。"
预期：derived 5 条，换算式 `5 nm = 0.005 μm`、`85.3% = 0.853`、`85 Ω = 0.085 kΩ`、`73.4% ≈ 73%`；320 Ω verbatim 保留 → PASS。

## 反例台账 T6（删除关键段无理由 + 缺决定）
```jsonl
{"source_pid":"S001-P003","action":"保留","reason":"方法要点保留"}
{"source_pid":"S001-P004","action":"删除","reason":""}
```
预期：ledger FAIL（exit=2）：unreasoned_action（S001-P004）+ missing_decision（列出 S001-P004）。

## 反例台账 T7（文件缺失）
retention_decisions.jsonl 不存在。预期：ledger FAIL（exit=2）：decisions_file_missing，列出全部关键段落 pid。

## 正例台账 T8
5 段各有保留/压缩决定且理由充分（见 examples/minimal_example.md）。预期：ledger OK，exit=0。
