# CHANGELOG

## v2.0.3（2026-11-25）

- 迭代背景：父辈 v1.0.1 平台重放评分 58/100；v1 仅交付 Markdown，无 Office 可编辑
  产物与真实渲染预览（运行时契约明确期望 editable outputs + rendered previews）。
- 新增 `make_docx.py`：纯标准库最小 OOXML 生成 translation.docx / bilingual.docx
  （标题层级映射、双语 〔PID〕 坐标保留）；LibreOffice 尽力转 PDF；
  preview_status.json 记录 docx/pdf 状态与降级原因。
- SKILL.md 新增第 11-12 步（可编辑交付物 + 交付确认抽查）。
- 本地合成案例实测：docx 结构校验通过；本环境 LibreOffice 可用，
  translation.pdf / bilingual.pdf 真实渲染成功；降级路径（无 soffice）记录正确；
  validate_output PASS。

## v1.0.1（2026-11-19）

- 首个提交版本（数字台账 + 双向比对）。平台评分 58/100。
