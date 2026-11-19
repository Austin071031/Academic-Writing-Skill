# 合成测试文本（标注：合成，非正式案例）

## 测试 1：缺译检出

源文：> We prepared the solution. The annealing temperature was 100 °C.
译文（只译第一句）：> 我们配制了溶液。
预期：P-s2 missing（高）；bilingual.md 显示【缺译】；coverage<1 → status 须 partial。

## 测试 2：图表编号一致性

源文题注：> Figure 1. Device architecture. / Table 1. Efficiency statistics.
译文（故意错号）：> 图1. 器件结构。 / 表2. 效率统计。
预期：图表编号集合 {1,1} vs {1,2} 不一致 → “图表编号不对应”（高）。

## 测试 3：长度疑似

源文：> Devices stored at 85 °C showed no significant degradation over 500 h, which
> indicates that the encapsulation effectively blocks moisture ingress.
译文（漏译从句）：> 器件在85 °C下储存500 h。
预期：比例 ≈ 0.35 < 0.55 → suspect_length（中），Agent 复核确认漏译从句并补译。

## 测试 4：未知 ID

译文 JSONL 含 {"seg_id":"P099-s1","translation":"……"}（segments 中无此 ID）。
预期：assemble 记入 unknown_seg_id；align audit 报“译文含未知句段ID”（中）。

## 反例稿（应零误报）

源文：> The catalyst shows 95% selectivity. / Figure 1. Structure of the catalyst.
译文：> 该催化剂选择性为95%。 / 图1. 催化剂结构。
预期：aligned=2，missing=0，图表编号一致，零 finding。
