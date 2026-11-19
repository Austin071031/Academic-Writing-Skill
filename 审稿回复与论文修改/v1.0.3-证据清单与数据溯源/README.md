# 审稿回复与论文修改 Skill · v1.0.3 证据清单与数据溯源

玻尔产品周赛第四期「审稿回复与论文修改」参赛作品（方向四：证据补充）。

## 这是什么

一个可被 Agent 调用的 Skill：读入基线稿件 + 审稿意见清单，完成受控返修的同时，把"证得住"做成可核验的工程——为每条需要补实验、补数据、补文献或重做分析的意见自动建立证据档案（EV 条目），标明到位状态与出处；交付前再把回复信与修订稿中的每个数字逐条溯源到基线段落行号或意见原文，来源不明的数字自动进入人工确认清单。

## 与基础 Agent 的差异（创新点）

1. **证据需求自动建档**：扫描 comments/dispositions/edit_plan 三份中间产物，为 needs_evidence 子要求自动生成 EV 条目（需求类型按 action_kind 映射），状态三档初判（到位/部分到位/无法补做）+ 替代说明模板，Agent 终判后重跑保留修订；
2. **共享证据去重**：dispositions 引用同一 EV 编号的多个子要求只建一条档案，条目内列全部 sub_id，杜绝"同一文献清单在三条意见里各写一遍、状态互相打架"；
3. **数字级溯源**：回复信与全部已落稿修改中的每个数字（含百分数）逐一与基线全文、意见原文比对，四档判定（溯源成功→baseline P### 行号 / 意见给出→comments sub_id / 待补 / 未核实），带边界的数字检索防止 1450 误命中 45、编号 R1/E3 误当数据；
4. **未核实数字自动进人工确认**：未核实数字连同 ±20 字上下文自动并入 manual_confirmations.json（幂等去重），exit=2 告警不硬失败——数字可能确属作者掌握，但必须留痕，不得无声带过。

## 快速开始

平台自动加载时无需手工操作；独立复用见 [docs/USAGE.md](docs/USAGE.md)。判定标准与红线见 [SKILL.md](SKILL.md) 与 [references/evidence_rules.md](references/evidence_rules.md)。

## 目录

```
SKILL.md            技能本体（八步工作流 + 12 类异常表）
scripts/            9 个纯标准库脚本（共享核心 8 个 + evidence_engine 主攻）
references/         数据契约（schemas）/ 证据规则（evidence_rules）
templates/          证据清单手工填写模板
checklists/         交付前自查清单
evaluation/         评分点-机制对照自查表
examples/           最小调用示例（合成，标明为示例）
docs/USAGE.md       使用说明
```

## 依赖与限制

Python 3.8+ 标准库；PDF 材料可选依赖 pdftotext（缺失时降级并记录）。只修订输入中实际提供的基线；不补做实验、不编造数据与文献；数字溯源只核对"是否出现过"，语义是否用对仍由 Agent 复核；未到位证据一律【待补】占位 + 清单 + 人工确认。

## 维护

版本：v1.0.3（2026-11-19）。仓库：https://github.com/Austin071031/Academic-Writing-Skill （目录 `审稿回复与论文修改/v1.0.3-证据清单与数据溯源`）。问题反馈请开 issue。
