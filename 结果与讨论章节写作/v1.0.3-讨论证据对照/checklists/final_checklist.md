# 交付前自查清单

## A. 契约与产物

- [ ] result.json 含 output_contract 全部字段 + case_id + status + sources + uncertainty + change_log
- [ ] results_and_discussion.md、claim_evidence_matrix.md、citation_report.json 均存在
- [ ] 环境有 pandoc/LaTeX 时已生成 docx/pdf，否则已注明

## B. 证据对照（本 Skill 核心）

- [ ] citation_report.json verdict = PASS
- [ ] 讨论段每个论断句带【数据：…】或【文献：…】锚
- [ ] 正文所有引用逐条匹配材料参考文献列表
- [ ] 每条文献对照都说明了关系（一致/不一致/部分一致）与可能原因
- [ ] 矩阵中无证据锚的论断未进入正文
- [ ] 机制推测全部标注"（推测，尚待验证）"
- [ ] 无凑数引用：删除任何讲不出关系的引用

## C. 事实一致与诚实性

- [ ] 数据锚只引用 data_anchors.md 已登记条目
- [ ] 转述文献结论未超出材料（题录/正文）实际提供的信息
- [ ] uncertainty 列出文献列表解析问题、无法判断的关系等
- [ ] change_log 记录被删除/修正的引用及原因
