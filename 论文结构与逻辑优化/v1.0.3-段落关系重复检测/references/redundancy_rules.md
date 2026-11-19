# 段落关系与重复判据（redundancy.py 规则说明，可复核）

## 1. 相似度体系（shingle / 阈值）

- **字符 3-gram shingle**：`scanutil.shingles` 取中英文与数字字符的连续 3-gram 集合，对语序局部重排稳健、对措辞变化敏感。Jaccard = 交集/并集。
- **内容词 terms**：中文二字组 + 英文实词（去停用词），`scanutil.terms`，用于衔接与拆分分析（词级而非字符级）。
- 阈值（`scanutil.THRESH`，全部写入 redundancy_report.json.thresholds）：

| 判据 | 阈值 | 含义 |
|-|-|-|
| para_duplicate | 0.55 | 段落字符 3-gram Jaccard ≥0.55 → 重复 |
| para_near | 0.30 | 0.30–0.55 → 近似重复（同义复述/分叉表述） |
| sentence_dup | 0.80 | 句子级跨章近重复 |
| gap_lex | 0.05 | 同章相邻段内容词重叠下限 |
| split_avg_sim | 0.03 | 长段内部句子两两平均相似度上限 |
| split_min_char | 400 | 拆分候选的最小段落字符数 |

- 依据：3-gram Jaccard 0.55 以上意味着两段约一半以上字符片段共享，几乎不可能是独立论述；0.30–0.55 是"同义复述/部分共用素材"的典型区间；0.80 的句子级阈值允许个别虚词差异。

## 2. 重复处置：同段/同章/跨章差异

- **同章相邻重复**（段序差 1）：`merge`——两段本属于同一论述流程，合并为一段，保留核心句、删去复述句。
- **同章非相邻重复**：`merge`——同章出现两次同一论述，保留先出现且角色更核心者，另一段差异句并入。
- **跨章重复**：`merge`（删除+交叉引用）——保留启发式：角色核心度 method/experiment/results/discussion（3）> introduction/conclusion（2）> abstract/related_work（1）；同分取文档序在先者。被删侧改为一句"详见 X 节"式交叉引用，避免读者在两章读到同一论证。
- **结构性呼应**（摘要↔引言、结论↔摘要，Jaccard≥0.55）：不自动判死。摘要点题、结论回收承诺是文体要求；但展开性复述（摘要 3 句讲同一实验细节）是冗余。词面方法不可分 → 单独成表，confidence=0.5，人工裁决：保留"研究对象+主要结论"骨架句，删除展开句。

## 3. 衔接分析（比 six_scan 更深）

- six_scan 只查相邻段重叠<0.05 且无 CONNECTIVES；本引擎在此基础上加：
  - **回指悬空**：段首匹配 ANAPHOR_CUES（如前所述/如上所述/上文/据此/由此/this shows/these results/as shown above…），但其内容词与前 3 段（全文序）交集为空 → 读者无法定位所指，必须补锚点。
  - 适用范围限定：references/acknowledgment 章不参与衔接判定（列举性内容天然低重叠）。
- CONNECTIVES 词表见 `scanutil.CONNECTIVES`（然而/此外/因此/However/Moreover/Therefore/…）。后段有衔接词开头即视为已作衔接，不重复报。

## 4. 拆分触发条件（该拆分未拆分）

触发（同时满足）：
1. 段落 n_char ≥ 400；
2. 内部句子数 2–30（超出说明切分器可能失效，跳过防爆）；
3. 句子两两平均 terms-Jaccard < 0.03——所有句子两两比较取均值，单句数少时该值稳定；<0.03 说明段内话题几乎句句不同（多话题混杂）。

建议拆分点：对每个句界 k，计算前半拼接 vs 后半拼接的内容词 Jaccard，取**最低**句界——即"前一半与后一半差异最大"的位置。拆分后两段各设主题句并补衔接（add_transition）。

## 5. findings 生成与截断

- 每类问题映射到统一 schema（`scanutil.make_finding`），dimension ∈ {redundancy, paragraph_relation}。
- 置信度：重复对按相似度线性 0.6→0.9；结构性呼应固定 0.5；句子级 0.7；近似重复 0.55；回指悬空 0.65；衔接缺失 0.55；拆分 0.6。
- 上限 MAX_FINDINGS=15，按 段落重复 > 结构性呼应 > 句子重复 > 近似重复 > 回指悬空 > 衔接缺失 > 拆分 顺序截断——重复类问题信息价值最高，拆分类最低（可由作者通读发现）。

## 6. 统计口径

- n_duplicate_pairs：Jaccard≥0.55 的段落对数（不含结构性呼应）。
- paragraphs_involved：去重后的涉及段落 ID。
- estimated_redundant_chars：每对重复中较短段的字符数之和——上界估算（合并后至多可省这么多字符）。
