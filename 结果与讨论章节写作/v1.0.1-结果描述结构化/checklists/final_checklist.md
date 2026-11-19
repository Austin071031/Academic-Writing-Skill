# 交付前自查清单（本方向特有项 + 通用项）

## A. 契约与产物

- [ ] result.json 含 output_contract 全部字段 + case_id + status + sources + uncertainty + change_log
- [ ] results_and_discussion.md 含可识别的「结果」「讨论」小节标题
- [ ] outline.md 存在：组织模式选择 + 理由、逐段段旨、发现编号覆盖
- [ ] 环境有 pandoc/LaTeX 时已生成 docx/pdf 预览，否则已在 result.json 注明

## B. 结构（本 Skill 核心）

- [ ] check_structure.py 输出 PASS（全部 R 系列检查通过）
- [ ] 结果段无解释性/因果性/评价性词汇（R1–R3）
- [ ] 结果段每段有图表锚点（R4），段落长度均衡（R5）
- [ ] 讨论段机制推测全部带标注（R6）
- [ ] outline 中全部发现条目在正文出现（R7）
- [ ] 阴性结果与意外观察有独立条目，未被省略

## C. 事实一致

- [ ] 正文数值与材料一致（抽查 3 个以上关键数值回原文核对）
- [ ] 引用全部出自材料参考文献列表，未虚构
- [ ] 无材料之外的事实进入正文

## D. 诚实性

- [ ] uncertainty 列出结构误报说明、材料缺口、需人工确认项
- [ ] change_log 记录结构与内容上的实质性修正
- [ ] 未伪造运行状态、脚本输出或文件
