# 06 · 代理评测（自造 case，真实运行数字）

基线 = v1.0.1（attempt 89028 同内容）；候选 = v2.0.0。自造 case 均非平台材料：
p1 正常（docx 稿件 + docx 模板 + 完整契约）；p2 劣化（case.json 非法 JSON，材料仍在同目录）；p3 空输入（无 case.json/材料）；p4 崩栈模拟（缺 inspect_case.py）。

| 指标 | 基线 v1.0.1 | 候选 v2.0.0 |
|-|-|-|
| 合法 result.json /4 | 3/4（p4 零产物） | 4/4 |
| 阶段失败计数（p1） | 0 | 0 |
| p1 合规核验 | 21 PASS / 0 FAIL / 0 WARN | 21 PASS / 0 FAIL / 0 WARN |
| p1 保真核验 | PASS | PASS |
| p1 result.json 契约键 | 3/3 filled | 3/3 filled（键集合与基线逐一同） |
| p2（劣化）status | failed | **success**（C3 修复命中） |
| p3（空输入）status | failed（诚实） | failed（诚实，行为一致） |
| p4（崩栈模拟） | 无 result.json | result.json（status=failed，诚实） |
| 最坏耗时（p1 全流程） | 4.0s | 4.0s（预算 900s 内） |
| 模型调用 | 0 | 0（预算不变） |

结论：基线全绿指标零变红；弃权型缺口 C1/C3 有真实修复证据。候选通过淘汰规则，可提交。

（长文档 TOC 预算守卫 C4 与 LO profile C5 为代码路径加固，本环境无可复现的反例场景，按代码审查计入，不编造测试数据。）
