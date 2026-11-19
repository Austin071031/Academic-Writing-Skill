# 评分对照表（自评用，对照周赛评审维度）

| 维度（满分） | 本版本对应能力 | 证据（运行产物） |
|-|-|-|
| 实际效果（40） | 术语异写逐处定位（pid+原文+异写率）；dangling 交叉引用检出并阻塞交付闸门；矛盾候选跨章配对；影响面一键列出 pid 清单 | `consistency_report.json/md`、`xref_audit.json`、`contradiction_candidates.json`、`impact_report.json/md` |
| 使用增益（25） | Agent 不用全文人肉比对：scan 一次给出全部候选；review 一次审定，引擎逐处核查；改稿后复跑自动复核异写清零 | SKILL.md Phase 2-4；glossary_review → glossary 的两步分工 |
| 创新增益（15） | 术语规范化（小写/连字符/全半角/单复数）+ 定义处豁免 + 最长命中去重；结论句主语两侧并集 n-gram 跨章极性比对；改动影响面三类传播（术语/xref/结论重叠） | references/consistency_rules.md §2/§4/§6 |
| 可靠体验（10） | Phase 0 骨架 result 防超时空手；40 次请求预算兜底；dangling 非空时 validate 硬 FAIL；引擎只出候选不自动判错；11 类异常处置表 | SKILL.md §3/§4；validate_output.py 联动 |
| 生态贡献（10） | 复用 shared-core 八脚本接口零修改；xref_audit.json 的 dangling 字段被共享 validate_output 直接消费；判据表独立成 references 可移植 | scripts/ 与 shared-core 一致；references/consistency_rules.md |

## 自评检查单
- [ ] 3 个隐藏案例全部产出 result.json 且 output_contract 字段齐全
- [ ] validate_output PASS 或如实 partial（附 issues）
- [ ] 每个案例都有 glossary.md + consistency_report.md（即使术语候选为空也要有空报告与说明）
- [ ] 矛盾候选逐对有裁决记录
- [ ] 预算内完成（≤64 请求/900 秒），超时走 partial 路径
