# 交付前自查清单（逐项打勾，任一不满足不得交付 success）

## 答得全
- [ ] comments.json 经 Agent 复核（拆分/类型/**needs_evidence**/action_kind 已确认或修正）
- [ ] 每个子要求在 dispositions.json 有 decision + ≥20 字 response
- [ ] 每条意见 id 出现在 response_letter.md
- [ ] 每个 needs_evidence 子要求都关联至少一条 EV（evidence_checklist.json 无漏项）

## 改得准
- [ ] edit_plan 所有锚点逐字抄自 structure.json
- [ ] revision_engine exit=0（无 failed_anchor）
- [ ] verify_revision 的 location 检查 PASS
- [ ] 可执行的文本修改全部落稿，未以"缺材料"为由跳过

## 证得住（本方向核心）
- [ ] evidence_engine demand 已运行；每条 EV 的 status 经 **Agent 终判**（非脚本初判照搬）
- [ ] 共享证据只建一条 EV 且列出全部 sub_id，dispositions 引用一致
- [ ] "无法补做"条目均有替代说明（原因 + 等效佐证/局限声明 + 去向），并列入 manual_confirmations
- [ ] "部分到位"条目的【待补】占位写清"缺什么、向谁要"，证据到位前未删除
- [ ] 回复信引用 EV# 与到位状态，未把占位说成已完成

## 数字溯源
- [ ] evidence_engine provenance 已运行且 provenance_report.md 已交付
- [ ] 未核实数字已逐条处置：确认出处（留档 manual_confirmations）或改【待补】后重跑
- [ ] "意见给出"的数字未误报为未核实；"待补"数字未冒充已核实
- [ ] 基线数字的语义使用经 Agent 复核（溯源只核对出现过，不保证用对）

## 对得上
- [ ] verify_revision 五重检查 overall PASS
- [ ] validate_output PASS
- [ ] result.json 的 status 与 verification/溯源结果一致（有未处置告警不报 success）
- [ ] change_log / evidence_map / uncertainty / manual_confirmations 已填写

## 诚实边界
- [ ] 无编造数字与文献条目（provenance + fabrication 双重检查通过）
- [ ] 无冒称补实验/已接收/联网核验的表述
- [ ] 材料缺口与异常写入 exceptions 且 status 相应降级
