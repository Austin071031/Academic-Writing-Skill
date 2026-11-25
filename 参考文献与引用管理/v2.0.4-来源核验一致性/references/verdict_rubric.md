# 论断—文献匹配裁决判据（四档）

裁决对象：**一个正文论断句** × **该句引用标记对应的条目**（library.json 的 R 编号）。
只依据材料内信息（条目 title/venue/year/字段、若有 abstract 则可用；正文论断句原文）。
不得凭记忆断言文献真伪；材料不足一律 insufficient_evidence 并写明缺什么。
rationale 必须同时引用双方原文短语（论断句片段 + 条目字段片段）。

## supports（直接支撑）

判据：条目主题与论断主题一致，且条目内容类型能够承载该论断（综述条目可支撑领域共识性论断；
实验条目可支撑其标题所示现象/方法的存在性论断）。数值型论断只有条目明确相关且材料未冲突时才给 supports。

例 1：论断"硅在嵌脱锂过程中体积变化超过 300%"，条目题名为 "Volume Expansion of Silicon Electrodes"
（J. Electrochem. Soc. 2018）→ supports。rationale：条目题名 "Volume Expansion" 直接对应论断"体积变化超过300%"。

例 2：论断"Chan 等人报道了硅纳米线在循环中保持结构完整"，条目作者含 Chan、题名含
"silicon nanowires" 与 "cycling" → supports。

例 3：论断"石墨烯包覆可提升硅负极循环稳定性"，条目题名为 "Graphene-coated silicon anodes with
improved cycling stability" → supports。

## partially（部分支撑）

判据：条目与论断主题相关，但只覆盖论断的一部分；或条目是更宽泛/更狭窄的相邻主题。
常见于：论断含多个分句、条目只支撑其一；条目是综述而论断是具体数值；条目年份/对象与论断略有出入。

例 1：论断"硅负极容量高但循环差"，条目只谈容量（题名 "High capacity silicon anodes"）→ partially
（支撑"容量高"，不支撑"循环差"）。

例 2：论断"纳米化可缓解体积膨胀并提升首效"，条目只谈纳米结构的应力缓解 → partially。

例 3：论断"[3-5] 共同表明纳米结构硅负极被广泛研究"，其中 [4] 是纳米线、[5] 是多孔硅，但 [3] 是
石墨负极综述 → 对 [3] 判 partially 或 unrelated（视题名相关度；此处 3 与纳米硅无关，应判 unrelated，
本例说明多标记要拆到单条目分别裁决）。

## unrelated（对不上）

判据：条目主题与论断主题明显不同；或条目作者/对象/年份与论断所叙矛盾。这是最严重的
"引用不匹配"，必须给出双方主题各是什么。

例 1：论断"硅体积膨胀导致粉化"，所引条目题名为 "Photocatalytic degradation of dyes" → unrelated。

例 2：论断"Chan 等人报道了硅纳米线"，条目作者为 Wang 且无纳米线内容 → unrelated
（点名作者的论断被不相关作者的条目支撑）。

例 3：论断"该材料在 2020 年首次合成"，条目年份 2015 且主题不符 → unrelated。

## insufficient_evidence（证据不足）

判据：材料内信息不足以判断匹配性。触发情形：条目只有题名没有摘要且题名笼统；
条目字段大面积缺失；正文论断含糊无法定位主题。**必须**在 rationale 写明缺什么、补什么能判。

例 1：条目仅有题名 "Studies on silicon"，论断"硅负极循环性能显著改善" → insufficient_evidence
（缺摘要/关键词，无法确认 "Studies" 是否涉及循环性能）。

例 2：条目 field_presence 全 false（只剩一个题名），任何具体论断都 → insufficient_evidence。

例 3：论断"前述方法效果良好"（"前述"回指不明）且引用标记 [2] → insufficient_evidence
（论断主题本身未在句内陈述，缺回指对象）。

## 输出纪律

- 每个带引用正文段落的**每个论断句**都要有一行裁决；宁可多判 insufficient_evidence 也不漏判。
- 一句多个引用标记（如 [2,3]）→ 对该句给一行总裁决，entry_ids 列全部；若各条目档位不同，
  在 rationale 中逐条目说明（引擎审计会校验 entry_ids 存在性）。
