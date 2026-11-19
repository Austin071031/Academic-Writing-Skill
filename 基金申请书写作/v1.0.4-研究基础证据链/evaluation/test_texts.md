# 合成测试文本（标注：全部为合成材料，非正式案例）

> 以下草稿段均假定置于 `# 研究基础与可行性` 节内；FID 编号引用合成台账
> （F0034=pub_mention Joule/来源 prior_work，F0038=pub_mention ZL202210123456.7/来源 prior_work，
> F0026=number 200 m²/来源 prior_work）。

## 测试 A：拟开展写成已完成体

草稿段（markers 含〔拟〕）：
> 本课题下一阶段已完成放大效率复测〔拟〕。

预期：aspect_violation_planned_as_done（high）×1（完成信号：已、完成）。

## 测试 B：已完成成果写成拟开展体

草稿段（锚定成果类〔F〕，材料记载该论文已见刊）：
> 申请人拟将相关成果整理投稿至 Joule 期刊〔F0034〕。

预期：aspect_violation_done_as_planned（medium）×1（拟态信号：拟、将）。
注：若句中同时出现 发表/建立 等完成信号，体貌判 mixed，本规则不命中——建议 Agent 拆段。

## 测试 C：成果断言无来源锚定

草稿段（无任何〔F〕标记）：
> 申请人发表高水平论文多篇，已获授权专利数项，主持国家级项目。

预期：unsourced_achievement（high）×1（成果信号：论文、专利、项目、发表、授权）。

## 测试 D：证据链不完整

- evidence_chain.json 存在但某行 relation_to_project="" → chain_incomplete（medium）×1/空行。
- evidence_chain.json 不存在（仅 seed）→ chain_incomplete（low）×1「未生成审定版 evidence_chain.json」。

## 测试 E：可行性信号缺失

草稿节只写成果罗列（无 可行/条件/保障/平台/团队/基础 任一词）。
预期：feasibility_missing（low）×1。

## 测试 F：正例零误报

草稿段（带真实 FID、体貌自洽）：
> 申请人已发表 Joule 期刊论文〔F0034〕，建立了界面修饰的方法学基础；
> 已获授权发明专利一项〔F0038〕。平台方面，已建立 200 m² 中试线〔F0026〕，
> 团队现有博士生 5 名，可行性依据充分。本课题拟在中试线上开展放大验证〔拟〕。

预期：feasibility_engine audit 对该节 0 high / 0 medium（aspect/unsourced 均不命中；
已完成段 completed 带〔F〕、〔拟〕段 planned 自洽、可行性信号齐备）。

## 测试 G：章节缺失

草稿无任何研究基础/可行性要素节。
预期：missing_section（high）×1。
