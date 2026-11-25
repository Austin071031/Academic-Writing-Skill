# 基础 Agent 常见失败模式（本 Skill 的针对性防线）

对照组（不加载 Skill 的基础 Agent）在"来源核验"任务上的典型失败，及本 Skill 的防线。

## 失败 1：凭印象断言"文献真实/编造"

- 表现：模型凭训练记忆说"这条 Nature Energy 论文确实存在"或"这个 DOI 看起来是假的"，
  材料里根本没有可核对的字段，或不做任何检查直接给结论。
- 危害：幻觉背书（把编造条目认证为真）比漏报更糟，直接违反诚实红线。
- 本 Skill 防线：
  - SKILL.md 红线 + verdict_rubric 规则 2/3：Agent **只判匹配、不判真伪**；真伪交给引擎的
    确定性体检（材料内字段）与可选 Crossref 联网。
  - 引擎体检逐条给 evidence 字符串（正则命中原因、年份值、缺失字段名），可独立复核，不靠模型口径。

## 失败 2：不逐句判匹配，只给笼统结论

- 表现：只写"整体引用基本合理"或抽查一两个引用，大量带引用段落没有裁决。
- 危害：漏判 = 未核验，评审视为未完成；遗漏的错配引用是最高价值发现。
- 本 Skill 防线：
  - 覆盖率审计：引擎比对"带引用正文段落"与 match_verdicts.jsonl 的 pid 集合，
    缺漏写入报告"裁决覆盖审计"并在 annotated_manuscript.md 插 `⚠ 缺裁决` 注释。
  - Phase 2 要求每个论断句一行；预算兜底宁可批量 insufficient_evidence 也不许漏段落。

## 失败 3：证据不足不标注，硬判 supports

- 表现：条目只有题名、无摘要，模型脑补内容判 supports；材料不足时不写明缺什么。
- 危害：虚假的 supports 会误导作者相信引用可靠；违反"证据可核验"评分项。
- 本 Skill 防线：
  - verdict_rubric 明确 insufficient_evidence 触发情形与"必须写明缺什么"的格式要求；
    空 rationale 被引擎审计记 `verdict_no_rationale` issue。
  - 非 supports 裁决（partially/unrelated/insufficient_evidence）会在标注稿句后插
    `<!-- ⚠ verdict: ... -->`，人眼与 diff 都能直接看到。

## 失败 4：离线假装联网核验成功

- 表现：沙箱无网络，模型仍声称"已查证 DOI 有效"。
- 本 Skill 防线：联网只能由 verify_engine.py --online 执行（urllib + timeout=5 + try/except）；
  任何异常统一记 `unverified_offline`；离线默认模式的报告明确写
  `not_attempted_offline_mode` 与诚实声明"未核验 ≠ 造假"。

## 失败 5：发现编号问题就手改正文数字

- 表现：audit 发现越界/缺口后直接改稿件里的 [n]。
- 本 Skill 防线：红线 3——编号一致性只报告不改号；修复属v1.0.1 renumber 流程
  （走 mapping.json + 引擎重排），本 Skill 交付物 annotated_manuscript.md 保留原编号。

## 失败 6：编造"核验通过"的条目级结论充数

- 表现：输出"4 条文献全部核验通过"之类无证据总结。
- 本 Skill 防线：verification_report.json 逐条目列 checks 数组与 evidence；
  summary 由引擎统计生成，Agent 无机会改写统计口径。
