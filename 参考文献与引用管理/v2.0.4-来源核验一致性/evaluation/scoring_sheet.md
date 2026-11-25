# 自查评分表（对照 SPEC-common 评分维度，目标 ≥80）

## 实际效果 40

| 子项 | 分值 | 自查证据 | 自评 |
|---|---|---|---|
| 任务完成度 15 | 15 | 两层核验全部落地：5 项本地体检 + 可选 Crossref 联网；四档裁决汇总；覆盖审计；编号一致性并入报告（/tmp/tc 自测 conclusion=issues_found，缺漏=无） | 14 |
| 正确性 15 | 15 | R002 三条 suspicious 均给出可复核 evidence；标注插入位置经阴性用例验证（缺裁决→段落行尾 ⚠）；阴性用例（坏 verdict/坏 entry_id/空 rationale）均被审计捕获 | 13 |
| 完整性 5 | 5 | result.json 含 case_id、output_contract 全字段（alias 回填 evidence/changes/status）；uncertainty/exceptions/stats/evidence_map 齐 | 5 |
| 可核验性 5 | 5 | verification_report.json 机读 + md 人读 + annotated 标注稿三方互证；每条裁决/体检有 rationale/evidence | 5 |

## 使用增益 25

| 子项 | 分值 | 自查证据 | 自评 |
|---|---|---|---|
| 质量 15 | 15 | 基础 Agent 的三类典型失败（凭印象断真伪/不逐句判/证据不足硬判 supports）各有机制防线（failure_modes.md 逐条对应） | 13 |
| 效率 5 | 5 | 机械劳动全在引擎（<30s）；Agent 只需写 match_verdicts.jsonl（目标 ≤6 次调用）；预算兜底给出批量 insufficient_evidence 路径 | 5 |
| 可验证 5 | 5 | 报告所有结论可回溯到材料内字段与正则/相似度算法；离线/联网状态如实 | 5 |

## 创新增益 15

| 子项 | 分值 | 自查证据 | 自评 |
|---|---|---|---|
| 新能力 5 | 5 | 条目级"真实性体检"与论断级"引用匹配裁决"双层次是本系列（v1.0.0–v1.0.3 整理/重排/去重方向）之外的新能力；缺漏审计 + ⚠ 缺裁决标注 | 5 |
| 方法 5 | 5 | 引擎体检确定性算法（DOI 注册语法/年份窗口/字段自洽/库内重复度>0.95+同作者）+ Agent 四档主题匹配 + Crossref 三态联网降级，方法文档化 | 5 |
| 证据 5 | 5 | 每条体检 evidence 字符串、每条裁决 rationale（强制引用双方原文短语，空 rationale 被审计记 issue） | 4 |

## 可靠体验 10

| 子项 | 分值 | 自查证据 | 自评 |
|---|---|---|---|
| 易用 3 | 3 | SKILL.md Phase 0-5 逐字命令；异常处置表 9 类；README/USAGE 快速开始 | 3 |
| 稳定 4 | 4 | py_compile 全通过；validate PASS；render_previews 必出 preview.html；超时/断网/坏文件均 try+降级 | 4 |
| 异常 3 | 3 | 异常表 + 超时空手保护（init_result 第一步）+ partial 降级路径 | 3 |

## 生态贡献 10

| 子项 | 分值 | 自查证据 | 自评 |
|---|---|---|---|
| 文档 3 | 3 | README/USAGE/CHANGELOG/examples + references/ 5 篇方法文档 | 3 |
| 可复用 4 | 4 | verify_engine.py 独立可跑（--library/--manuscript/--verdicts/--work/--out/--online）；共享 8 脚本接口未改 | 4 |
| 分享 3 | 3 | GITHUB_URL.txt 一行仓库地址 | 3 |

合计自评：约 91（保守）。
