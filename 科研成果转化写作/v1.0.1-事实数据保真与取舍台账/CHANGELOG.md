# CHANGELOG

## v1.0.1（2026-11-19）
- 事实数据保真核验引擎 `fidelity_engine.py check`：
  正向逐值核验（number/percent/sample/figure_ref/table_ref → verbatim/derived/missing/altered，
  derived 含百分比↔小数、±1% 四舍五入、nm↔μm 等单位换算、"由 A 降至 B"端点重算，报告写换算式）；
  反向逐 token 溯源（unverified 源外新数值 = critical）；图表编号双向一致性；
  年份/化学式/章节号遮蔽防误报。
- 内容取舍台账 `fidelity_engine.py ledger`：逐段保留/压缩/删除决定校验
  （关键段落必须有决定、删除必须给理由），生成人读台账（before 摘要/动作/理由/涉及事实/丢弃事实）。
- 共享核心：骨架 result.json、case 解析、源文事实清单、逐段对齐、assemble/validate/render 闸门。

## v1.0.0（2026-11-19）
- 基线版本（受众适配与可读性方向），见 `v1.0.0-受众适配与可读性/`。
