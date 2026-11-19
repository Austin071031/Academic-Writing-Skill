# 方法：引用三方核验（citation-verifier）

## 三方一致性
1. **编号一致**：文内引用集合 = 参考文献表集合。文内有而表无 → error（挂空引用）；表有而文内未用 → warning（冗余引用）；
2. **著录完整**：字段 = 作者/年份/题名/出处（期刊或出版社）/卷期页/DOI。缺项进 missing_fields；
   同一文献多个版本（预印本 vs 正式发表）记 version_note，著录以正式版本为准；
3. **逐字支持**：被引文献必须挂 evidence.csv 摘录并经 R5 命中；命中失败 = 引用了但不支持（或支撑了相近但更弱/更强的句子），记 error。

## 二手转引
摘录或著录出现 “as cited in / 转引自 / 见某某引” → secondary=true：该证据降级为 background，
因为二手转引无法据此判断原文真实表述，必须在 citation_audit.csv 注明并建议补原文。

## 撤稿与版本
仅当材料本身提供撤稿/更正信息时记录；否则在 verification_path 给出可回查路径
（DOI 解析链接、Crossref 检索式、期刊页面检索式），verification_status=offline_unverified。
**离线环境禁止声称已完成联网核验。**

## 可回查路径格式
- 有 DOI：https://doi.org/<doi>
- 无 DOI：Crossref 查询式 “TITLE:<题名> AND AUTH:<第一作者>” 或期刊名+年+卷期页检索式
每条路径须使第三方在 5 分钟内独立复现核验。
