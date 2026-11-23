# CHANGELOG

## v1.5.0（2026-11-23）— 编辑批注工作流（首版）

- 核心机制：诊断→处方双段制（先看清再动刀）；置信度三级（high/medium/low），
  low 级一律 action=confirm 不生效，处方照写并开人工确认卡。
- 交付双形态手稿：annotated_manuscript.md（`[E#]~~原文~~ → **改文**[/E#]` 批注标记）
  与 polished_full.md（apply 生效版）；edit_cards + acceptance_checklist 支撑逐条裁决。
- 作者反馈可回流任务画像（声明不接受某类改动），形成可持续协作闭环。

- 提交：playground attempt 99597（product-arena-02-7051d92d，写作02｜学术语言润色）
