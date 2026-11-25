# CHANGELOG

## v2.0.1（2026-11-25）

- 迭代背景：父辈 v1.0.1 平台重放评分 58/100；v1 的 result.json 契约字段为别名兜底，
  多字段指向同一 outputs 汇总，可核验性/完整性受损（且同名字段 uncertainty 曾被
  outputs 覆盖，本版已在 assemble_result 修复：同名字段保留原值）。
- 新增 `contract_fill.py`：output_contract 逐字段关键词语义匹配 →
  {file, sha256, bytes, summary, content_preview, verified} 结构化条目；
  内置数据字段保护；contract_override.json 人工映射；未映射置 null + uncertainty。
- SKILL.md 新增第 11-12 步（契约填充 + Agent 复核 override）。
- 本地合成案例实测：4 字段契约映射正确（含内置字段保留）；override 无效文件回退正常；
  validate_output PASS。

## v1.0.1（2026-11-19）

- 首个提交版本（数字台账 + 双向比对）。平台评分 58/100。
