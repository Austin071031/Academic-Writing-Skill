# 评分自查表（交付前逐项核对）

| 评分点 | 自查问题 | 对应机制 |
|-|-|-|
| 任务完成度 | 是否对完整稿件完成诊断并交付可执行编辑计划（含重组大纲）？ | 8 步工作流 + edit_plan.json + restructured_outline.md |
| 结果正确性 | 是否删净误报、补全漏报、无虚构缺陷？ | 第 7 步 Agent 判断 + failure_modes.md 复核清单 |
| 结果完整性 | 六维是否都有结论（含"未检出"说明）？ | six_scan.py 六维普查 + report_builder 全维度分节 |
| 结果可核验性 | 每条问题能否按位置+锚点指回原文？阈值是否可查？ | evidence_map + scanutil.THRESH + section_map.json |
| 质量增益 | 是否优于"通用写作建议"？ | 角色序列逆序对表、篇幅占比表、缩写首现表、重组大纲草稿 |
| 效率增益 | 机械劳动是否全部脚本化？ | 管线秒级完成，Agent 只做 3 类判断 |
| 新增能力 | 基础 Agent 不具备什么？ | 章节级叙事顺序机检（逆序对枚举）+ 信息释放顺序定位（缩写/回指） |
| 运行稳定性 | 平铺文本/PDF/截断/多稿件/短文档/综述文体是否都有降级路径？ | 异常表 9 类 + init_result 骨架 + genre 豁免 |
| 异常处理 | status 是否与 uncertainty/exceptions 一致？ | validate_output 闸门 |
| 文档完整性 | USAGE/示例/限制/维护信息是否齐全？ | docs+examples+CHANGELOG |

## 合成自测（evaluation/test_texts.md）

用 `test_texts.md` 中的合成稿件 T1 跑通 8 步：预期命中——顺序倒置（结果先于方法）1 条、核心缺失（结论）1 条、篇幅失衡（结果章 >55%）1 条、缩写首现未定义（LIBs 等）≥1 条、方法性描述混入结果章 1 条；`section_map.json` 与 `restructured_outline.md` 生成；`validate_output.py` 必须 PASS。T2 用于验证"顺序正常稿件不误报逆序、已定义缩写不误报"。
