# CHANGELOG

## v2.0.2（2026-11-25）

- 迭代背景：父辈 v1.0.1 平台重放评分 58/100；题面固定案例任务类型不限于整篇翻译
  （校对/修订/双语写作），v1 单分支管线在非翻译案例上完成度受损。
- inspect_case 升级：task_type 四类识别 + 材料角色判定（source/existing_translation）+
  校对任务缺译文文件的 issues 提示。
- 新增 `align_existing_translation.py`：已有译文按长度比例映射回句段坐标，
  异常映射标 needs_review；直接生成 translations.jsonl 复用全套机检与交付。
- SKILL.md 改为分支工作流（A/B/C + 公共阶段）。
- 本地合成案例实测：校对任务识别正确（proofread_translation + tracked 形态）、
  译文对齐/告警/机检链路贯通；validate_output PASS。

## v1.0.1（2026-11-19）

- 首个提交版本（数字台账 + 双向比对）。平台评分 58/100。
