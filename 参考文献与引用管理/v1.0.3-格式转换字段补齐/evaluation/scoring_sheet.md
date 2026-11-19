# 自查评分表（v1.0.3｜格式转换与字段补齐）

运行 `/tmp/tc/input` 合成案例后逐项核对。满分 100，目标 ≥80。

## 实际效果（40）

| 项 | 分 | 判据 |
|---|---|---|
| 任务完成度 | 15 | converted_refs.txt + references.md 覆盖 library.json 全部条目；目标规范正确（task.md 提 GB/T → gbt2015_numeric） |
| 正确性 | 15 | 抽查 3 条：作者截断正确（>3 加 等/et al）、`Smith, John`→`Smith J`、卷(期):页 结构完整、DOI 原样、类型标识正确（期刊[J]/会议[C]）、中文条目全角/英文条目半角 |
| 完整性 | 5 | field_audit.json 覆盖每一条记录；convert_report.md 四节齐全 |
| 可核验性 | 5 | 每条缺失字段有 `not_provided` 记录；补齐有 `copied_from_Rxxx` 来源；report 有前后对照 |

## 使用增益（25）

| 项 | 分 | 判据 |
|---|---|---|
| 质量 | 15 | 字段保留率 ≥95%；标点无误用；无臆造字段（report 第 4 节即缺失清单） |
| 效率 | 5 | 转换+审计一条命令完成，Agent 仅判定风格与审查 |
| 可验证 | 5 | validate_output.py PASS；preview.html 存在 |

## 创新增益（15）

| 项 | 分 | 判据 |
|---|---|---|
| 新能力 | 5 | 跨条目字段互补（copied_from_Rxxx）与 unverified 联网探测为基础 Agent 所无 |
| 方法 | 5 | 映射表声明式外置（format_specs/*.md + gbt_type_tags.md 运行时解析） |
| 证据 | 5 | field_audit.json / convert_report.md / stats.json 三处证据互相印证 |

## 可靠体验（10）

| 项 | 分 | 判据 |
|---|---|---|
| 易用 | 3 | SKILL.md Phase 0-5 命令逐字可执行 |
| 稳定 | 4 | 空库/损坏文件/无网络均不崩溃，exit code 语义正确 |
| 异常 | 3 | 异常表 8 种情形各有记录落点（exceptions.json / uncertainty.json） |

## 生态贡献（10）

| 项 | 分 | 判据 |
|---|---|---|
| 文档 | 3 | README/USAGE/worked_example 齐全 |
| 可复用 | 4 | format_specs 数据文件可被其他版本/工具直接解析复用 |
| 分享 | 3 | GITHUB_URL.txt 一行有效链接 |

## 一票否决（诚实红线）

- 出现任何臆造字段值（缺 DOI 被"补上"非材料来源的值）→ 0 分，返工。
- field_audit 中 `not_provided` 缺失字段却出现在最终条目里 → 0 分，返工。
