# 论文结构与逻辑优化 — 提交与得分记录

- 赛题：玻尔产品周赛第四期「论文结构与逻辑优化」（challenge-8021aacb）
- 评分方式：平台 Harbor worker 真实运行评审（human/harbor review，scoreMax=100）
- 提交账号：A0516；提交时间：2026-11-19（UTC）；出分时间：2026-11-20（UTC）

## 得分总览（5/5 全部出分，status=final）

| 迭代版本 | 主攻方向 | Attempt | 得分 | 评审反馈摘要 |
|-|-|-|-|-|
| v1.0.1-章节结构叙事 | 章节结构与叙事顺序 | 89588 | **66.00** | Solid — refine for a more complete and rigorous solution. |
| v1.0.0-研究问题贡献对齐 | 研究问题与贡献主张对齐 | 89587 | **65.33** | 同上 |
| v1.0.2-论证链论据映射 | 论证链与论据对应 | 89589 | **64.67** | 同上 |
| v1.0.3-段落关系重复检测 | 段落关系与重复内容 | 89590 | **64.33** | 同上 |
| v1.0.4-结论边界核验 | 结论边界与表述尺度 | 89591 | **63.67** | 同上 |

最高分：**v1.0.1-章节结构叙事（66.00，attempt 89588）**；五版分差 2.33 分，方向间差异不显著。

## 版本架构说明

五版共享同一确定性脚本管线（init_result → inspect_case → parse_manuscript → six_scan 六维普查 → 主攻引擎 → report_builder → assemble_result → validate_output），各版仅更换主攻引擎与 references：

- v1.0.0 `rq_engine.py`：RQ×角色章节覆盖矩阵、贡献×证据三档裁决、首尾呼应矩阵（rq_map.json）
- v1.0.1 `section_flow.py`：角色序列逆序对、篇幅占比分析、缩写首现未定义、重组大纲（section_map.json + restructured_outline.md）
- v1.0.2 `chain_audit.py`：论断四型分类、strong/weak/none 锚点分档、循环论证近似检出、强度匹配（chain_audit.json）
- v1.0.3 `redundancy.py`：段落 shingle 重复对、句子级跨章重复、回指悬空、拆分候选（redundancy_report.json）
- v1.0.4 `boundary_audit.py`：数字三层溯源（舍入一致性容差）、摘要-结论一致性、因果三档、推广超界、限制审计（boundary_audit.json）

## 复盘（下一轮迭代方向）

得分集中在 63–66 区间，距 80 分目标的主要缺口（结合评审口径"more complete and rigorous"）：

1. **Agent 判断层未充分利用**：平台运行时模型预算 64 请求/900s，本版交付物以脚本草稿为主，DeepSeek Harness 在真实案例上的"删误报/补漏报/总体诊断"深度可能不足——下轮应在 SKILL.md 中强制逐条复核并产出总体评价段落。
2. **六维覆盖偏浅**：six_scan 每维度 ≤8 条启发式候选，真实长稿件的主要断裂可能漏检；主攻引擎 findings 上限 15 条可能截断真实问题。
3. **证据强度**：evidence_map 为自动抽取，缺少"改前/改后对照"示例化呈现，可核验性分项有提升空间。
4. **白板对照增益**：质量/效率增益是相对基础 Agent 评估，需在报告中显式呈现"基础 Agent 通常只给通用建议 vs 本技能的定位级编辑动作"的对照说明。

## 链接

- 仓库目录：`论文结构与逻辑优化/v1.0.0-研究问题贡献对齐` ~ `v1.0.4-结论边界核验`；v2 迭代 `v2.0.0-复核闭环主通道` ~ `v2.0.4-交叉引用审计`
- 赛题页面：https://play.bohrium.com/challenge/challenge-8021aacb

## v2.0.x 五方向单点迭代批次（父辈 v1.0.1 / 89588 / 66.00，2026-11-25 提交，待出分）

迭代协议：资产守恒（父辈 8-9 个脚本 md5 一致，引擎除 v2.0.4 外零改动）、每版只改一处针对
评审口径（"more complete and rigorous"）的提分点；回归证据见各版本目录 `regression_report.json`
（机器真跑生成）。GitHub 附加分：仓库保持 private（用户决策），本轮仅做内容提分。

| Attempt | 版本 | 单点改动（唯一一件事） | 命中维度 | 状态 |
|-|-|-|-|-|
| 106682 | v2.0.0-复核闭环主通道 | review_helper pack/apply：候选问题+±1段原文上下文打包，Agent 逐条裁决（采纳/修正/驳回+理由）+总体诊断回写报告 0.5 节，预算表 ≤12 请求 | 实际效果（正确性/严谨性）、使用增益 | submitted |
| 106684 | v2.0.1-契约语义对齐 | contract_check 逐字段语义映射（重叠打分+justification+coverage 三档），assemble/validate 联动，missing 如实登记 | 任务完成度、结果可核验性 | submitted |
| 106685 | v2.0.2-改后对照预览 | apply_preview：9 类 op 确定性改前/改后模板（标注建议示例），注入报告与 edit_plan | 改得动、任务完成度、质量增益 | submitted |
| 106686 | v2.0.3-增益自证卡 | gain_card：六维覆盖/锚点率/可执行率/定位粒度机器可复算 + 基础 Agent 反事实对照表，嵌入报告 | 使用增益可验证、创新证据 | submitted |
| 106687 | v2.0.4-交叉引用审计 | section_flow 增 xref_audit：图/表/公式/章节/文献编号悬空 + 未引用条目（T3 合成稿四类全命中） | 结果正确性（不漏真实断裂）、链得通 | submitted |

- 出分后将回填本表；若某方向显著提分，下一批以该方向为新父辈。
