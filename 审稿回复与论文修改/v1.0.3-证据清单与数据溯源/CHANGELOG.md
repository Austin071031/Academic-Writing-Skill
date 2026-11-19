# CHANGELOG

## v1.0.3（2026-11-19）

- 方向：证据补充（证据清单与数据溯源）。
- 共享核心：init_result / inspect_case / parse_manuscript / parse_comments / revision_engine / verify_revision / assemble_result / validate_output（纯标准库，复用 _core；assemble_result 的交付物清单新增 provenance_report.md）。
- 主攻引擎 evidence_engine.py（--stage demand|provenance）：
  - demand：为 needs_evidence 子要求自动建 EV 档案（demand 按 action_kind 映射四类需求；dispositions 引用同一 EV 编号或同意见同需求的子要求共享去重；三档状态初判 + 替代说明模板；Agent 手工修订后按 sub_ids 匹配保留，可安全重跑）；产出 work/evidence_checklist.json 与 evidence_checklist.md 草稿；
  - provenance：回复信 + 全部 applied op new_text 的数字逐条溯源（带边界检索防误命中；四档判定：溯源成功→baseline P### 行号 / 意见给出→comments sub_id / 待补 / 未核实）；未核实数字连同 ±20 字上下文幂等并入 work/manual_confirmations.json，exit=2 告警不硬失败；自动生成 work/evidence_map.json 与 provenance_report.md。
- 文档：SKILL.md（八步工作流：步骤 4.5 证据建档 + 步骤 7 数字溯源，12 类异常表）、evidence_rules（四类需求定义 / 三档状态判据 / 三类替代说明句式 / 数字溯源规则）、证据清单模板、自查清单、评分对照表、合成最小示例。
- 本地合成案例端到端冒烟：2 条 EV（R1-C1 两子要求共享 EV1 去重正确）；17 个数字溯源（12 溯源成功 / 3 待补 / 2 未核实进人工确认）；demand 重跑保留 Agent 终判；provenance 重跑幂等；verify/validate PASS。
