# 交付前一致性自查清单（逐项打勾，任一不满足不得交付 success）

## 三方对账（核心）
- [ ] consistency_engine exit=0（无任何 FAIL 项）
- [ ] 每个 applied op 在对账报告第 2.1 节有落点区域（✅ 落在差异区域内）
- [ ] 回复信中每个 E# 引用均通过第 2.2 节校验（存在 + applied + 落在 diff region）
- [ ] 第 2.3 节无未认领 diff region；若有 WARN，已逐条人工确认并写入 manual_confirmations
- [ ] 纯空白豁免之外无被误判为噪音的真实改动

## 声称与版本对齐
- [ ] 回复信未引用 failed_anchor / 不存在的 E#
- [ ] 采纳/部分采纳的处置全部有 edit_ops 或 evidence 支撑（第 2.4 节无 FAIL）
- [ ] 回复信中的位置描述（章节/段落）与 edit_locations.md 及当前修订稿行号一致
- [ ] edit_locations.md 的行号取自本轮 edit_report，非凭记忆或上轮旧稿

## 承诺台账（多轮）
- [ ] 轮次读取正确（case.json constraints.round / revision_round，缺省 1）
- [ ] 历史回复文件已嗅探；round>1 未找到时在台账与 uncertainty 中注明
- [ ] 每条历史承诺有兑现状态；未兑现的在回复信中说明原因与新计划
- [ ] "无法判定"的承诺已列入 uncertainty
- [ ] 以【待补】占位兑现的承诺只记"部分兑现"，回复信同句说明占位

## 改得准（沿用共享核心）
- [ ] edit_plan 所有锚点逐字抄自 structure.json
- [ ] revision_engine exit=0（无 failed_anchor）
- [ ] 修订稿与基线存在真实差异（validate 内置检查）

## 证得住与诚实边界
- [ ] 每个 needs_evidence 子要求在 evidence_checklist.md 有条目与状态
- [ ] 回复信未把占位说成已完成；无编造数字；无冒称补实验/联网核验
- [ ] verify_revision 五重检查 overall PASS；validate_output PASS
- [ ] result.json 的 status 与 consistency/verification 结果一致（FAIL 未报 success）
- [ ] change_log / uncertainty / manual_confirmations / stats 已填写
