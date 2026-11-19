# 评分自查表（交付前逐项核对）

| 评分点 | 自查问题 | 对应机制 |
|-|-|-|
| 任务完成度 | 是否对完整稿件完成诊断并交付可执行编辑计划（合并/拆分/衔接建议）？ | 8 步工作流 + edit_plan.json |
| 结果正确性 | 是否删净误报（方法章标准表述、摘要点题呼应）、补全漏报、无虚构缺陷？ | 第 7 步 Agent 判断 + failure_modes.md 复核清单 |
| 结果完整性 | 六维是否都有结论（含"未检出"说明）？ | six_scan.py 六维普查 + report_builder 全维度分节 |
| 结果可核验性 | 每条问题能否按位置+锚点指回原文？阈值是否可查？ | evidence_map + scanutil.THRESH + redundancy_report.json.thresholds |
| 质量增益 | 是否优于"通用写作建议"？ | 段落重复对表（keeper 启发式）、句子级跨章重复、冗余字符估算、建议拆分句界 |
| 效率增益 | 机械劳动是否全部脚本化？ | 管线秒级完成，Agent 只做 3 类判断 |
| 新增能力 | 基础 Agent 不具备什么？ | n-gram 级重复定位 + 回指悬空/拆分候选机检（redundancy_report.json） |
| 运行稳定性 | 平铺文本/PDF/截断/多稿件/超量段落是否都有降级路径？ | 异常表 8 类 + init_result 骨架 + 两两比较防爆上限 |
| 异常处理 | status 是否与 uncertainty/exceptions 一致？ | validate_output 闸门 |
| 文档完整性 | USAGE/示例/限制/维护信息是否齐全？ | docs+examples+CHANGELOG |

## 合成自测（evaluation/test_texts.md）

用 `test_texts.md` 中的合成稿件（T1）跑通 8 步：预期命中——跨章段落重复（引言⇄相关工作）≥1 条、摘要⇔结论句子级近重复 1 条、相邻段话题跳变≥1 条、≥400 字符混杂段拆分候选 1 条、"如前述"回指悬空 1 条；`validate_output.py` 必须 PASS。
