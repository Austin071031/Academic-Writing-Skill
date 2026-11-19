# CHANGELOG

## v1.0.3（2026-11-19）

- 初始版本：跨源一致性核验。新增 cross_source_check.py：detect 阶段机检同名参数跨源
  多值冲突（数值归一化），verify 阶段校验裁决覆盖率（resolved/escalated/unresolved）。
- 共享骨架同源，独立自包含。
- 独有规则 consistency_rules.md（三级优先级、裁决格式、别名归并、豁免情形）。
