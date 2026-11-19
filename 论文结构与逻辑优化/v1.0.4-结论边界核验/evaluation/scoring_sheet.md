# 评分自查表（交付前逐项核对）

| 评分点 | 自查问题 | 对应机制 |
|-|-|-|
| 任务完成度 | 是否对完整稿件完成诊断并交付可执行编辑计划？ | 8 步工作流 + edit_plan.json |
| 结果正确性 | 是否删净误报、补全漏报、无虚构缺陷？ | 第 7 步 Agent 判断 + failure_modes.md 复核清单 |
| 结果完整性 | 六维是否都有结论（含"未检出"说明）？ | six_scan.py 六维普查 + report_builder 全维度分节 |
| 结果可核验性 | 每个数字的 verdict 能否按 matched_source/rel_diff 复核？ | evidence_map + boundary_audit.json 逐条溯源表 |
| 质量增益 | 是否优于"避免夸大结论"的通用建议？ | 数字三层溯源、因果三档、范围比对、限制四态审计 |
| 效率增益 | 机械劳动是否全部脚本化？ | 管线秒级完成，Agent 只做 3 类判断 |
| 新增能力 | 基础 Agent 不具备什么？ | 结论数字逐条溯源机检 + 摘要-结论数字一致性比对（boundary_audit.json） |
| 运行稳定性 | 平铺文本/PDF/截断/多稿件是否都有降级路径？ | 异常表 7 类 + init_result 骨架 |
| 异常处理 | status 是否与 uncertainty/exceptions 一致？ | validate_output 闸门 |
| 文档完整性 | USAGE/示例/限制/维护信息是否齐全？ | docs+examples+CHANGELOG |

## 合成自测（evaluation/test_texts.md）

用 `test_texts.md` 中的合成稿件跑通 8 步：预期检出无源数字 2 条（91.0%、65.8%）、容差内 approx 1 条（65%）、摘要-结论数字不一致 1 条、因果超界 1 条以上、绝对化 1 条、推广超界 1 条、缺局限性说明 1 条；`validate_output.py` 必须 PASS。
