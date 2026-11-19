# 交付前自查清单（逐项打勾，任一不满足不得交付 success）

## 答得全
- [ ] comments.json 经 Agent 复核（拆分/类型/严重度/**action_kind** 已确认或修正）
- [ ] 每个子要求在 dispositions.json 有 decision + 对症 response + tone
- [ ] 回复信覆盖全部意见 id 与子要求 id（audit 的 letter_structure PASS）
- [ ] 信尾"总体修改清单"与"待办与确认"已生成且无未处置 ⚠ 项

## 改得准
- [ ] edit_plan 所有锚点逐字抄自 structure.json
- [ ] revision_engine exit=0（无 failed_anchor）
- [ ] disposition 引用的每个 op 在 edit_report 中 status=applied（回复信无 ⚠ 指涉）
- [ ] 修订稿与基线存在真实差异

## 证得住
- [ ] 每个 needs_evidence 子要求在 evidence_checklist 有 EV# 条目与状态
- [ ] add_experiment/add_data/add_citation/reanalysis 类回应均引 EV# 或写明待补/无法/补做（audit off_topic PASS）
- [ ] 无法补做的条目有替代说明，修订稿对应位置有【待补】占位
- [ ] 回复信未把占位说成已完成

## 对得上
- [ ] response_engine audit 四项全 PASS（off_topic / tone_consistency / tone_redlines / letter_structure）
- [ ] 手工润色回复信之后已重跑 audit 并仍 PASS
- [ ] verify_revision 五重检查 overall PASS
- [ ] validate_output PASS；result.json 的 status 与 verification 结果一致
- [ ] change_log / evidence_map / uncertainty / manual_confirmations 已填写

## 诚实边界
- [ ] 无编造数字（fabrication 检查无未说明的新数字）
- [ ] 无冒称补实验/已接收/联网核验的表述
- [ ] 无冒犯、过度承诺、无原则顺从措辞（红线扫描 PASS）
- [ ] 不采纳条目均有 ≥40 字依据且引基线锚点；材料缺口与异常写入 exceptions 且 status 相应降级
