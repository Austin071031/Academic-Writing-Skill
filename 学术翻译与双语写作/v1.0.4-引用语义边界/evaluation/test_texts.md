# 合成测试文本（标注：合成，非正式案例）

## 测试 1：引用缺失与新增

源文：> Stability improved significantly [5], consistent with reports (Zhang et al., 2023).
译文A（丢引用）：> 稳定性显著提升，与已有报道一致。 → 两处“引用标记缺失”（高）。
译文B（加引用）：> 稳定性显著提升[5][6]，与报道一致（Zhang et al., 2023）。 → “引用标记新增 [6]”（高）。

## 测试 2：否定范围丢失

源文：> The coating did not degrade under humid conditions.
译文（丢否定）：> 涂层在潮湿条件下发生降解。 → “否定范围丢失”（高）。

## 测试 3：语气升格

源文：> These results suggest the barrier may be effective.
译文（升格）：> 这些结果证明该阻挡层有效。 → “语气升格”（高）+ possibility/suggestion 丢失。

## 测试 4：限定与约数

源文：> Only three compositions were tested, with approximately ±0.3% uncertainty.
译文（丢限定）：> 测试了三种组分，不确定度为±0.3%。 → “限定条件丢失”（中）+“约数限定丢失”（中）。

## 反例稿（应零误报）

源文：> No degradation was observed over 500 h [5]. This may indicate good stability.
译文：> 500 h内未观察到衰减[5]。这可能表明稳定性良好。
预期：citation_fidelity=1.0；否定（未）与可能性（可能）保留；零 finding。
