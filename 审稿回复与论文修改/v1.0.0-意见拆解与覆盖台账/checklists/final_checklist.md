# 交付前自查清单（逐项打勾，任一不满足不得交付 success）

## 答得全
- [ ] comments.json 经 Agent 复核（拆分/类型/严重度已确认或修正）
- [ ] 每个子要求在 dispositions.json 有 decision + ≥20 字 response
- [ ] 每条意见 id 出现在 response_letter.md
- [ ] 拆解报告第 2/3 节的重叠与冲突均已处置并互相引用

## 改得准
- [ ] edit_plan 所有锚点逐字抄自 structure.json
- [ ] revision_engine exit=0（无 failed_anchor）
- [ ] verify_revision 的 location 检查 PASS（每处新文本在修订稿可找到）
- [ ] 修订稿与基线存在真实差异

## 证得住
- [ ] 每个 needs_evidence 子要求在 evidence_checklist.md 有条目与状态
- [ ] 无法补做的条目有替代说明，修订稿对应位置有【待补】占位
- [ ] 回复信未把占位说成已完成

## 对得上
- [ ] verify_revision 五重检查 overall PASS
- [ ] validate_output PASS
- [ ] result.json 的 status 与 verification 结果一致
- [ ] change_log / evidence_map / uncertainty / manual_confirmations 已填写

## 诚实边界
- [ ] 无编造数字（fabrication 检查无未说明的新数字）
- [ ] 无冒称补实验/已接收/联网核验的表述
- [ ] 材料缺口与异常写入 exceptions 且 status 相应降级
