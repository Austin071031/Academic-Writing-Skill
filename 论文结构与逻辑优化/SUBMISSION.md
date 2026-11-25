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

- 仓库目录：`论文结构与逻辑优化/v1.0.0-研究问题贡献对齐` ~ `v1.0.4-结论边界核验`
- 赛题页面：https://play.bohrium.com/challenge/challenge-8021aacb
