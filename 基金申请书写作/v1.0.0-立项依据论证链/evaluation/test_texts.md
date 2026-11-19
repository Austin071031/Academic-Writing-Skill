# 合成测试文本（标注：全部为合成材料，非正式案例）

## 测试 A：口号堆叠检出

草稿段（无〔F〕标记）：
> 钙钛矿太阳能电池研究意义重大，是实现双碳目标的国家战略迫切需求，近年来备受关注。

预期：rationale_engine audit 命中 slogan_without_evidence ×3（意义重大/国家战略…/备受关注）。

## 测试 B：现状论断无锚定

草稿段：
> 目前国内外学者已广泛研究界面钝化策略，现有工作表明钝化可显著提升效率。

预期：state_claim_unanchored（medium）×1。

## 测试 C：材料外数字

材料台账仅含 26.1%、380 mV。草稿写「效率已达 29.9%」（无〔拟〕）。
预期：source_audit high off_source_number ×1（29.9%）。

## 测试 D：论证链缺环

草稿立项依据只有现状与瓶颈，无任何「申请人/本团队/我们」表述。
预期：chain_link_missing high ×1（缺「我们」环）。

## 测试 E：正例零误报

草稿段（带真实 FID）：
> 认证效率已达 26.1%〔F0007〕，但开路电压损失仍高达 380 mV〔F0009〕。
> 申请人已建立瞬态光电压平台〔F0016〕。

预期：rationale audit 与 source_audit 对该段 0 findings。

## 测试 F：FID 不存在拦截

草稿使用〔F9999〕（台账无此条）。预期：draft_builder findings_draft high ×1。
