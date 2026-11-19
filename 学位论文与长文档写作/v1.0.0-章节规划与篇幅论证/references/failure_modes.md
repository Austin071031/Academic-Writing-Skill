# 已知失败模式与处置

| 失败模式 | 现象 | 处置 |
|-|-|-|
| 大纲无字数预算 | 全部条目 budget=None | 只做字数统计；不做偏差判定，stats 记录 budget_absent |
| 大纲与章节标题用词不同 | 直接映射失败，靠关键词命中 0 条 | Agent 在 chapter_plan.md 手工建立 oid↔sid 对应并写入 plan 覆盖 |
| 材料语义相关但字面不重合 | 关键词覆盖漏配 | Agent 人工复核 coverage，可手工把 pid 加入 evidence_pids |
| 章节稿混用编号体系 | 新章用了「第四章」而全文用「第4章」 | 统一为既有体系；check 的 heading_sequence_ok 复核 |
| 数字四舍五入超出 ±1% | 派生核验失败 | 改为原文值或在 uncertainty 说明舍入规则 |
| 多稿文件顺序错乱 | 章节树顺序与实际不符 | parse_chapters 按任务说明中的顺序显式传参，不靠文件名字典序 |
| 材料为大段无空行文本 | 分段兜底为逐行 | 已内置；若仍成一段，Agent 手工加空行后重跑 |
| pdf 提取丢表格 | 表格数据缺失 | exceptions 记录；表数据以文字材料为准 |
