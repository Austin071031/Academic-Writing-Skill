# 作者协同工作流（author workflow）

## 本 Skill 交付后，作者怎么用

1. 打开 `acceptance_checklist.md`：先看"需作者裁决"清单，逐条勾选。
2. 每条裁决对照 `edit_cards.md` 中同编号卡片（诊断/处方/理由/置信度）。
3. 打开 `annotated_manuscript.md` 通读：`[E#]` 锚点可跳到对应卡；
   接受 → 采用 polished_full.md 中的版本；拒绝 → 抄回原文。
4. 通用验收勾选（数值/引用/限定强度/术语/语域）逐项确认后即可投稿。

## 置信度语义

- high：客观硬错误（主谓一致、冠词、拼写），拒绝理由应当很充分。
- medium：惯例性改法（口语→书面、冗余删减），可按个人风格回退。
- low：判断性取舍（限定强度、术语选择、语义重述），默认未生效，需作者主动采纳。

## 反馈回流

作者拒绝的卡片类型可在下一轮任务画像中声明（"不接受 register 类改动"），
Agent 应在 task_profile.json 的 constraints 中记录并在诊断阶段跳过该类。
