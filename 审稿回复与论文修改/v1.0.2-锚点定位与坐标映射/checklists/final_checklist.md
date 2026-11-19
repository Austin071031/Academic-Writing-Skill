# 交付前自查清单（逐项打勾，任一不满足不得交付 success）

## 答得全
- [ ] comments.json 经 Agent 复核（拆分/类型已确认或修正，sub_id 连续）
- [ ] 每个子要求在 dispositions.json 有 decision + ≥20 字 response
- [ ] 每条意见 id 出现在 response_letter.md

## 改得准
- [ ] edit_plan 所有锚点逐字抄自 structure.json
- [ ] revision_engine exit=0（无 failed_anchor）
- [ ] 定位链路顺序正确：改 plan 后先 revision_engine 再 anchor_engine

## 对得上（本方向主攻）
- [ ] anchor_engine 生成 location_table.md，所有 applied op 均有双坐标（基线+修订侧各不缺）
- [ ] 变更区域表中每个区域关联 op 或标注"—"，无空转区域
- [ ] 模糊锚点预警已逐条人工复核并写入 manual_confirmations
- [ ] "锚点已由改写消除"的行已列入 uncertainty 说明
- [ ] 新增段落引用使用新段 ID + 修订稿行号（无虚构基线行号）
- [ ] response_letter.md 每处手改后已重跑 anchor_engine 且 exit=0
- [ ] 回复信中 E# 全部在 applied 集合内（引擎核验无"E引用悬空"）
- [ ] 回复信中 ≥8 字引文逐字存在于修订稿（引擎核验无"引文未找到"）
- [ ] 回复信中 P###/SEC#/第 N 行坐标全部合法（引擎核验无"坐标不存在/行号越界"）
- [ ] verify_revision 五重检查 overall PASS；validate_output PASS
- [ ] result.json status 与 verification 结果一致；change_log / uncertainty 已填写

## 证得住
- [ ] 每个 needs_evidence 子要求在 evidence_checklist.md 有条目与状态
- [ ] 无法补做的条目有替代说明，修订稿对应位置有【待补】占位
- [ ] 回复信未把占位说成已完成

## 诚实边界
- [ ] 无编造数字（fabrication 检查无未说明的新数字）
- [ ] 无冒称补实验/已接收/联网核验的表述
- [ ] 材料缺口与异常写入 exceptions 且 status 相应降级
