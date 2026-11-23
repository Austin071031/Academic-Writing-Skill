# 02 · 评分模型（细则逆向）

`rubric_source: official_verified`（赛题页 API 实读，权重=分值原样照抄，见 00_task_spec.md）。

| 维度 | 权重 | 基线拆解 | 目标拆解 | 支撑机制（可机检） | 对应脚本 | 基线覆盖 |
|-|-|-|-|-|-|-|-|
| 实际效果 | 40 | 无法拆解（无出分基线） | ≥56（目标80的0.7地板） | 模板实测检查项清单、结构化样式绑定、逐项合规核验、内容单元级保真比对、渲染导出核验 | measure_template / adapt_docx / compliance_check / fidelity_check / render_preview | ✅ 已覆盖 |
| 使用增益 | 25 | 同上 | 对照组可见的流程化执行 | 一键流水线（9 阶段自动）、人工复核点清单化 | run_pipeline / SKILL.md | ✅ 已覆盖 |
| 创新增益 | 15 | 同上 | 反向工程检查项、TOC 真页码、保真自动比对 | measure_template（反推）、toc 两遍回填、fidelity 字节级比对 | 同上 | ✅ 已覆盖 |
| 可靠体验 | 10 | 同上 | 崩栈必有合法产物、预算守卫、异常分类 | 顶层 guard、应急 result、form-feed 分页、LO profile、扫描兜底 | run_pipeline / render_preview | ⚠️ v1.0.1 部分 → v2.0.0 补齐 |
| 生态贡献 | 10 | 同上 | 文档齐备、direction 元数据、可复用脚本 | usage/spec_schema/troubleshooting/example + direction.json | 文档 + 新增 direction.json | ⚠️ v1.0.1 缺 direction → v2.0.0 补齐 |

地板法则：实际效果(40)+使用增益(25)=65% 为地板——v2.0.0 的加固不动这两个维度的任何既有机制（行为 parity 已验证：9 阶段状态、21 PASS、fidelity PASS 三项全同）。
折算法则：N=1（样本不足），所有预期不折算也不写乐观数（R9）。
