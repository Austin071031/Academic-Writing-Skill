# 合成测试文本（标注：合成，非正式案例）

## 测试 1：四舍五入检出

源文：> The certified efficiency was 23.4% with an open-circuit voltage of 1.18 V.
译文（故意改整）：> 认证效率为23%，开路电压1.18 V。
预期：23 vs 23.4 → “疑似四舍五入/笔误”（中），恢复 23.4%。

## 测试 2：跨语言量级等值

源文：> Approximately 1.2 million articles were indexed.
译文A（等值）：> 约120万篇论文被收录。 → matched，不报。
译文B（错误）：> 约12万篇论文被收录。 → 1.2e6 vs 1.2e5，十倍关系 → “疑似数字笔误”（高）。

## 测试 3：增译与缺失

源文：> The devices retained 92.0% after 500 h.
译文A（增译）：> 器件在500 h后保持92.0%，优于文献的85%。 → “增译数字 85%”（高）。
译文B（缺失）：> 器件在500 h后性能稳定。 → “数字缺失 92.0%”（高）。

## 测试 4：引用内数字屏蔽

源文：> Efficiency rose from 3.8% in 2009 to 25% in 2023 [2-4].
译文：> 效率从2009年的3.8%升至2023年的25%[2-4]。
预期：[2-4] 内 2、4 不参与比对；其余全 matched，零 finding。

## 反例稿（应零误报）

源文：> The bandgap is 1.55 eV, measured at 100 °C for 10 min.
译文：> 带隙为1.55 eV，在100 °C下测量10 min。
预期：fidelity=1.0，issues=0。
