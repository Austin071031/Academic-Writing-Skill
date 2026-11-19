# 速查表：引用核验清单（citation-verifier）

## 三方核验（每条引用必过）
1. 编号：文内 ↔ 文献表双向一致；2. 著录：作者/年/题名/出处/卷期页/DOI 缺项即报；
3. 支持：所挂摘录逐字命中原文（R5），失败=引用不支持该论断。

## 特殊标记
secondary=true：“as cited in/转引自”出现即标，证据降 background；
version_note：预印本/正式版本并存时著录以正式版为准；
offline_unverified：离线不能联网核验，给路径不声称已核。

## verification_path 格式
有 DOI：https://doi.org/<doi>；无 DOI：Crossref 查询式 TITLE+AUTH。
