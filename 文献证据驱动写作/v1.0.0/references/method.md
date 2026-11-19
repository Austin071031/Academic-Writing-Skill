# 方法：全文证据图谱（evidence-atlas）

## 为什么从全文而不是摘要
摘要由作者自撰、经过意图性筛选，且不含方法细节与局限性全文；以摘要为依据的“证据”在复核时无法定位到可判定的原文位置。
本 Skill 要求一切摘录来自 pdftotext/PyMuPDF 转换出的全文文本（/app/work/text/），并经脚本逐字命中核验（R5）。

## 文档画像
逐篇判定 doc_type，判定必须给出 structure_basis（看到的结构特征），不允许凭期刊名或感觉：
- primary_study：含方法（Methods/Materials）、结果（Results）、样本或数据规模描述；
- review：无原始样本、章节为综述结构（如“现有研究”“进展”）、引用密集；
- guideline：含推荐意见（recommendation）与推荐等级/证据等级；
- consensus：共识声明文件，含共识形成方法；
- preprint：题头或页眉标注 preprint/未经同行评议，或材料注明未正式发表；
- editorial：社论/评论，无原始数据；
- dataset：数据描述文件。
同一文档混合特征时取主导类型并在 reliability_note 说明。

## 摘录 SOP
1. 只摘录完整句（句号/分号收尾），单条 ≤300 字；
2. 优先摘录：含数值的结果句、方法关键句、作者明确结论句、局限性句；
3. 逐字摘录，禁止改写、概括、翻译后充当摘录；跨句拼接禁止；
4. location 必须可回查：p.N（页码，基于页标记）或 §x.y（章节号）；两者可得时都给；
5. 每条标 support_type：数据/方法/结论句→direct；背景与铺垫→background；作者自述局限→partial（对“该文证明了X”这类论断而言）；
6. 同一文档摘录控制在“覆盖该文核心主张所需的最小集合”，重复登记同句记 error。

## 机器可复现性
extract_text.py 的页标记使 location 可被脚本反查；validate_output.py 的 R5 用空白归一化子串匹配逐条命中摘录，
未命中的摘录是 error（意味着非逐字或张冠李戴）。该机制是本方向相对基础 Agent 的核心增益：基础 Agent 的“摘录”通常是改写或幻觉，无法机检。
