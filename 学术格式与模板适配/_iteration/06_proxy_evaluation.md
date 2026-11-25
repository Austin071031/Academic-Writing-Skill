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

## v2.1.x 批次代理评测（2026-11-25，父辈 v2.0.0 / 101404 / 58.6667）

自造 case 均非平台材料：p1 正常（docx 稿 + docx 模板，任务文本不含正文规格以
触发模板驱动路径；含 1 处孤儿引用 图2、5 处行距直改、文题块 2 段）；
p2 劣化（case.json 非法 JSON）；p3 空输入。

| 指标 | 父辈 v2.0.0 | v2.1.0 | v2.1.1 | v2.1.2 | v2.1.3 | v2.1.4 |
|-|-|-|-|-|-|-|
| p1 九阶段 success | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| p1 fidelity | PASS | PASS | PASS | PASS | PASS | PASS |
| p1 compliance（P/F/W/S） | 12/0/0/3 | **23/0/0/2** | 12/0/0/3 | 12/0/0/3 | **15/0/1/3** | 12/0/0/3 |
| p1 spec.body | {}（默认12pt） | **10.5pt 实测映射** | {} | {} | {} | {} |
| p1 残留行距直改 | 5 处 | 5 处 | **0 处** | 5 处 | 5 处 | 5 处 |
| p1 all_fonts_embedded | false（误判） | false | false | **true** | false | false |
| p1 题注/引用核验项 | 无 | 无 | 无 | 无 | **4 项（图2 孤儿 WARN）** | 无 |
| p1 文题字号 | 压成 12pt | 压成 10.5pt | 12pt | 12pt | 12pt | **保留 16pt** |
| p2（劣化）status | success | success | success | success | success | success |
| p3（空输入）status | failed（诚实） | failed | failed | failed | failed | failed |
| result.json 契约键 parity | — | ✅ 逐一同 | ✅ | ✅ | ✅ | ✅ |
| 契约字段填充 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

结论：五版父辈全绿指标零变红，各自方向指标有真实正向证据；全部通过淘汰规则，
已于 2026-11-25T03:46–03:47Z 提交（attempts 106656–106660）。
