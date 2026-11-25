# 去重判据：信号阈值表、裁决判据与正反例

## 1. 成对信号定义与阈值

| 信号 | 定义 | 归一化 | 说明 |
|---|---|---|---|
| title_sim | 题名字符 3-gram Jaccard | 0–1 | 先归一化：小写、去标点、去文献类型标记 [J]/[C]/[EB/OL]、去 "a review"/"review"/"综述"/"研究进展" 等价后缀、去 "arXiv preprint" 标记。CJK 与 Latin 分别计算；**跨语言对不可比（comparable=false，title_sim 记 0）** |
| doi_match | 归一化 DOI（去 https://doi.org/ 前缀、小写）完全一致 | bool | 两个不同 DOI 均存在且不同 → 直接保护 |
| year_diff | 年份差绝对值；任缺 → None | 年 | 缺失年份不参与自动合并 |
| author_overlap | 作者**姓氏**集合 Jaccard（"Smith, John"→smith；"张三"→张） | 0–1 | 姓氏粗匹配，重名会偏高，须结合题名 |
| venue_sim | 刊会名归一化字符 3-gram Jaccard | 0–1 | 跨语言刊会不可比 |
| type_compatible | same / preprint_formal / cautious / difficult | 档位 | 期刊↔预印本=preprint_formal 可合并；期刊↔会议=cautious 需谨慎；其余 difficult |

## 2. 三档处置规则（引擎）

| 档位 | 条件 | 处置 |
|---|---|---|
| auto_merge | doi_match；或 title_sim≥0.90 且 author_overlap≥0.5 且 year_diff≤1 | Agent 复核确认后合并 |
| protected | (a) 两个不同 DOI 均存在且不相同；或 (b) 同语种、同一第一作者、同年、title_sim<0.60 | **禁止合并**：不并入任何候选组；任何候选边不得把保护对连入同组；apply 对违反裁决硬拒绝 |
| needs_review | 其余有潜质的对 | Agent 逐组裁决（merge / keep_separate），理由必须引用信号值 |

跨语言补充规则：comparable=false 且 author_overlap≥0.5 且 year_diff≤1（或缺失）的对
自动标 `cross_language_hint`，提示"可能为同一文献的中/英文不同译名"，交 Agent 裁决。

## 3. Agent 裁决判据（Phase 3 必读）

**判 merge 需同时满足**：
1. 主题一致：同语种时 title_sim≥0.90；跨语言时题名词项语义对应（人工读题名判断），
   且 author_overlap≥0.5；
2. 作者组合一致或包容（一者为另一者的子集/超集，如预印本作者更多）；
3. 年份相容：year_diff≤1（预印本早于正式版一年属正常）；
4. 不触发保护：不存在两个不同 DOI；非"同作者同年但主题迥异"。

**判 keep_separate 的充分条件（任一）**：
- 题名主题差异明显（同语种 title_sim<0.60；跨语言时译名也对不上主题）；
- 作者组合不同（重合姓氏之外出现无法解释的新作者/缺作者）；
- 两个不同 DOI 均存在。

**keep_rid 选择**：正式版 > 预印本；字段更全者优先；同档位取期刊版。
预印本的 arXiv 号必须写入 keep 条目 extra_fields.arxiv_id。

## 4. 正反例（8 例）

**正例（应合并）**

1. **预印本↔期刊正式版**：题名归一化后完全相同（title_sim=1.0），作者姓氏重合 1.0，
   年份差 1（2019 预印本 / 2020 正式版），type_compatible=preprint_formal → 合并，
   keep 期刊版，arXiv 号进 extra_fields。
2. **中英文同译**：Smith 等《Silicon Anodes for Lithium-Ion Batteries: A Review》
   与《锂离子电池硅负极综述》，author_overlap=1.0、同年、comparable=false（跨语言）→
   needs_review 判 merge，keep 信息更全的正式版，另一语种的刊名/卷期记入差异说明。
3. **期刊版↔会议版（谨慎合并）**：同一作者、同年、题名为跨语言同译、
   type_compatible=cautious → 主题/作者/年份均一致才可合并，keep 期刊版，
   会议出处记入差异说明。
4. **数据库导出差异（字段互缺）**：同一 DOI 条目，其一缺卷期另一缺页码 →
   doi_match 自动合并候选，字段并集补全。

**反例（必须 keep_separate / protected）**

5. **同名作者陷阱**：Zhang, Wei 2021 年《Deep Learning for Battery State of Estimation》
   （J. Power Sources, DOI 10.1016/...）与 Zhang, Wei 2021 年《Deep Learning for
   Catalyst Screening》（Nat. Catal., DOI 10.1038/...）——第一作者相同、同年，但
   title_sim≈0.27 且两个不同 DOI → **protected，禁止合并**。基础 Agent 最常在此犯错。
6. **同名同姓不同研究**：Li, Ming 的两篇同年综述主题分别为钠电池与固态电解质，
   作者组合不同（合作者不一样）→ keep_separate，即使姓氏重合 1.0。
7. **同主题同年但实为两篇**：同课题组同年发表实验论文与评论文章（comment），
   题名相似但一为 research article 一为 commentary、卷期不同 → 谨慎 keep_separate，
   除非 DOI 相同。
8. **仅姓氏巧合**：作者列表分别为 [Lee K] 与 [Lee S]，author_overlap=1.0 但
   同名不同人、题名相似度低 → keep_separate；姓氏信号必须让位于题名与 DOI。

## 5. 置信与降级

- 信号任一为 None（缺年份/缺作者）→ 禁止自动合并，只能由 Agent 在理由中显式说明缺失；
- protected 对的判定写入 merge_report.md 与 exceptions，供评审复核；
- 引擎不出"翻译检测"结论——跨语言是否同译由 Agent 读题名判断，引擎只提供提示信号。
