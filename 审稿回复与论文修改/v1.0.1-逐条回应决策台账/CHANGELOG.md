# CHANGELOG

## v1.0.1（2026-11-19）

- 第二版。方向：逐条回应决策台账（含语气控制）。复用 v1.0.0 共享核心 8 脚本，不改动其核心逻辑。
- 新增主攻引擎 response_engine.py（纯标准库，--work --out [--stage generate|audit]）：
  - generate：回复信由 dispositions/edit_report/evidence_checklist 自动装配；审稿人→意见→子要求三级，引用原意见摘录（前 80 字）；每子要求输出 决策+回应+修改指涉（E# 及 status/行号）+证据指涉（EV#）；failed/缺失 op 自动标 ⚠ 并写入信尾问题清单与 work/response_problems.json；信首固定阅读说明，信尾自动生成总体修改清单与待办与确认。
  - audit：答非所问检测（按 action_kind 核验对症性）、决策-语气一致性（weak_reject/tone_mismatch/hollow_accept）、语气红线扫描（冒犯/过度承诺/无原则顺从，给四档句式改写建议）、信件完整性；任一 FAIL 即 exit 1，输出 audit_report.json。
- 新增 references/response_rules.md：决策分类法、四档语气句式库（接受/澄清/礼貌反驳/申诉）、答非所问判据表、语气红线词表（与引擎词表同步）。
- 文档全套：SKILL.md（八步工作流 + 12 类异常表）、USAGE、模板、自查清单、16 点评分对照表、合成最小示例。
- 本地合成案例端到端验收：revision_engine 5/5 应用 → generate 覆盖 R1/R2 全部 5 意见 7 子要求 → audit PASS；注入答非所问 disposition 后 audit 正确检出（exit=1），恢复后复跑 PASS；verify_revision 五重 PASS；assemble+validate PASS。

## v1.0.0（2026-11-19）

- 首版（意见拆解与覆盖台账），见 `../v1.0.0-意见拆解与覆盖台账/CHANGELOG.md`。
