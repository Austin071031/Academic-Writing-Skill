# 交付前自查清单

## A. 契约与产物

- [ ] result.json 含 output_contract 全部字段 + case_id + status + sources + uncertainty + change_log
- [ ] results_and_discussion.md 存在；环境有 pandoc/LaTeX 时已生成 docx/pdf，否则已注明
- [ ] causal_audit_report.json 存在且 verdict = PASS

## B. 因果边界（本 Skill 核心）

- [ ] 每条关键论断在 design_notes.md 中定级，正文措辞不越级
- [ ] 无级 B 设计支撑时，正文无因果动词（或全部带降级标记）
- [ ] 结果段无机制词汇；机制解释全部在讨论段且标注"（推测，尚待验证）"
- [ ] 级 C 因果句带条件边界（剂量/体系/时间窗）
- [ ] 转述他人文献时保持了原研究的因果强度

## C. 局限（本 Skill 核心）

- [ ] 局限覆盖方法/样本/测量/统计四层（缺省层在 uncertainty 说明依据）
- [ ] 每条局限含：具体内容 + 威胁对象与方向 + 改进路径
- [ ] 局限与正文结论强度联动一致（写了统计局限，相关结论措辞已降级）

## D. 诚实性

- [ ] 设计信息缺失时按观察性定级并已在 uncertainty 说明
- [ ] change_log 记录至少一处因果降级修改
- [ ] 无虚构数据、文献或运行状态
