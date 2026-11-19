# 交付前自查清单（逐项打勾，全部通过才提交）

## A. 契约与完整性

- [ ] `/app/output/result.json` 存在且包含 case.json `output_contract` 中的全部字段（字段名原样，不多不少）
- [ ] result.json 含 `case_id`、`status`（success/partial/failed）、`sources`、`uncertainty`、`change_log`
- [ ] `/app/output/results_and_discussion.md` 存在且含结果与讨论两部分（或题目只要求一部分时如实说明）
- [ ] 有 pandoc 则已生成 docx；有 LaTeX 则已生成 PDF 预览；都没有则在 result.json 注明

## B. 数值准确性（本 Skill 核心）

- [ ] `python3 scripts/verify_numbers.py --ledger ... --text ... --out ...` 输出 PASS（unmatched = 0）
- [ ] 每个数值的单位与材料一致；换算值已注明换算关系
- [ ] 每个 ± 值注明误差类型（SD/SEM/95% CI/unknown），与图注或方法一致
- [ ] 有效数字与材料一致，无多余位数
- [ ] 引用到面板级（图2B）与补充材料编号（图S1）正确
- [ ] 正文未出现材料之外的数字

## C. 结果与讨论分家

- [ ] 结果段只陈述观察，无机制解释词汇（因为/由于/表明/提示机制……）
- [ ] 讨论段每个论断有证据锚点（【数据：…】/【文献：…】）
- [ ] 机制推测已标注（推测，尚待验证）
- [ ] 阴性结果与不一致文献被如实交代，未被删除

## D. 诚实性

- [ ] uncertainty 列出全部读数不确定项、材料缺口与需人工确认项
- [ ] change_log 记录了写作中的实质性修正（如误差类型更正）
- [ ] 无任何虚构数值、虚构文献或伪造运行状态
