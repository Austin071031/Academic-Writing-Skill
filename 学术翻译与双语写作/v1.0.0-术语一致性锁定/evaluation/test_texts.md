# 合成测试文本（标注：合成，非正式案例）

## 测试 1：术语漂移检出

源文（合成）：
> Perovskite solar cells (PSCs) are promising. The perovskite solar cells show high
> efficiency. These perovskite photovoltaic devices are stable.

译文（合成，含故意漂移）：
> 钙钛矿太阳能电池（PSCs）很有前景。钙钛矿太阳能电池表现出高效率。这些钙钛矿光伏器件很稳定。

预期：若 declared_variants 未登记“钙钛矿光伏器件”，audit 对第三句报“术语未锁定”（中）；
登记后判合规。注意第三句源文实为变体表述（photovoltaic devices），Agent 复核可驳回。

## 测试 2：缩写首现全称

源文：> The hole transport layer (HTL) is essential. The HTL affects stability.
译文（合成，故意丢失缩写）：> 空穴传输层至关重要。HTL 影响稳定性。
预期：含 “(HTL)” 定义句段译文未保留 “（HTL）” → “缩写首现未给全称”（低）。

## 测试 3：受保护片段完整性

源文：> The efficiency reached 23.4% at 1.18 V [2], as shown in Figure 1.
译文（合成，正确）：> 效率在1.18 V下达到23.4%[2]，如图1所示。
预期：受保护片段 23.4% / 1.18 V / [2] 原样保留，segments.json 中 protected 计数一致。

## 反例稿（应零误报）

源文：> Lithium dendrites (Li dendrites) were observed. Lithium dendrites cause short circuits.
译文：> 观察到锂枝晶（Li dendrites）。锂枝晶会导致短路。
预期：glossary 锁定“锂枝晶”后 audit violations=0。
