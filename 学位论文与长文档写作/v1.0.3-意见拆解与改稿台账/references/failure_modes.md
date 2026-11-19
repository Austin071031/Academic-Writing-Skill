# 典型失败模式（failure_modes）

1. **臆造意见**：工单只有 3 条，Agent"顺手"多改了几处自认为不好的地方。
   → 只处理 workorder_items.json 里的条目；额外发现的问题写 uncertainty.json，不直接改。

2. **假装落实**：意见无法定位，Agent 在台账里写"已修改"但文本没变。
   → 状态只由引擎判定；before/after 必须来自真实文本，diff_report 可证伪。

3. **改丢原意**：补充"两步烧结区别"时把原文"目标 5.0 mS/cm"改没了。
   → replace 前把原文关键数据抄进 new_text；Phase 4 复核 diff。

4. **覆盖原件**：直接改写 /input 下章节文件，无法回退。
   → 修改只在 work/revised/；引擎自动备份 work/original/；/input 永不写入。

5. **漏条**：agent_edits.json 只写了容易的几条，难题目漏掉。
   → 每条 pending 意见三选一（edit/skip/defer）；漏条会被引擎标"待人工确认"并计数。

6. **冲突双落实**：补充派与删除派意见落在同一段，两条都改，结果自相矛盾。
   → locate 检出 conflict 后必须裁决：一 edit 一 skip/defer，理由入台账。

7. **模糊定位臆改**：pid 对应不上时凭感觉找一段替换。
   → 引擎模糊定位失败即判"无法落实+原因"；Agent 不得绕过引擎手改 revised 后声称落实。

8. **diff 不可读**：交付只说"已按意见修改"，作者看不出改了什么。
   → diff_report.md 提供行级 unified diff；台账每条有 before/after 摘录。

9. **多轮混乱**：第二轮意见与第一轮已落实内容矛盾，两份修改叠加出病句。
   → round 升序执行；后轮覆盖前轮时台账注明覆盖关系，Phase 4 复核净效果。

10. **超时空手**：把时间花在逐条润色上，最后 result.json 都没有。
    → Phase 0 先落骨架；预算吃紧时批量 defer + 立即走 apply/version/交付（status=partial）。
