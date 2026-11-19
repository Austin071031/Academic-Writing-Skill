# CHANGELOG

## v1.0.0（2026-11-19）

- 首版。方向：意见拆解与覆盖台账。
- 共享核心：init_result / inspect_case / parse_manuscript / parse_comments / revision_engine / verify_revision / assemble_result / validate_output（纯标准库）。
- 主攻引擎 decompose_engine.py：子要求矩阵、跨意见重叠/冲突/证据依赖检测、first/audit 双阶段覆盖台账。
- 文档：SKILL.md（八步工作流 + 9 类异常表）、schemas、拆解规则、诚实边界、回复信模板、自查清单、评分对照表、合成最小示例。
- 本地合成案例端到端冒烟：5 意见 7 子要求全覆盖，锚点歧义/失效正确拦截，verify/validate PASS。
