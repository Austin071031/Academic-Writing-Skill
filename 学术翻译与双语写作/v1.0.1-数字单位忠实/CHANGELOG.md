# CHANGELOG

## v1.0.1（2026-11-19）

- 首个提交版本。数字台账 + 跨语言量级归一 + 双向逐值比对（缺失/增译/改动三档/单位差异）。
- 引用标记内数字屏蔽；万/亿↔million/billion 等值判定；千分位/科学计数/%/‰ 归一。
- 本地合成案例端到端实测：四舍五入、十倍笔误、增译、缺失、120万↔1.2 million 等值
  均按预期判定；validate_output PASS。详见 evaluation/test_texts.md（合成）。
