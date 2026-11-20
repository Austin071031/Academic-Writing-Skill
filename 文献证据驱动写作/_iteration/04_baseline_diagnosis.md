# 阶段 4 基线确认（baseline diagnosis）

基线 = **v1.0.1（claim-source-mapper / claim-source-linking）**，attempt 89152，**70.0**（platform_verified，台账最高分；89153 pending 不参与）。
判定：70.0 ≥ 目标 80 × 0.7 = 56 → **基线健康，走阶段 5 方向迭代**（非契约层修复）。
v1.0.2（89153）execStatus=failed 但未出分、原因不可归因于 Skill 本体，不构成"契约层弃权"证据；其余四版全部正常出分，说明契约层（result.json 全字段 + 三段交付）已被平台接受。

## 机制资产白名单（§2.3，回归比对基准）

| 资产 | 做什么 | 被谁读取 |
|-|-|-|
| `scripts/inspect_case.py` | 解析 case.json/task.md → brief.json（case_id、契约键、材料盘点、issues） | run_pipeline.sh |
| `scripts/extract_text.py` | 材料文本化（pdftotext→fitz→pypdf）→ 带页标记文本 + text_manifest.json | run_pipeline.sh；validate_output.py（R5 文本库） |
| `scripts/init_result.py` | result.json 骨架早存（契约键递归复制 + case_id + partial） | run_pipeline.sh |
| `scripts/validate_output.py` | R1 契约递归覆盖 / R2 三段产物 / R3 claims 结构 / R4 evidence 结构 / R5 摘录逐字命中（页码反查）/ R6 成稿覆盖论断 / R7 方向专属（读 direction.json） | 阶段5 |
| `scripts/run_pipeline.sh` | 阶段0 一键预检 | Agent |
| `direction.json` | 方向标识 + 机检参数 | validate_output.py R7 |
| `references/output_spec.md` | claims/evidence/draft/result.json 字段规范 | Agent 写作依据 |
| `references/method.md` + `rubric.md` | 切分规则、五值支撑、status 推导 | Agent 判定依据 |
| `references/edge_cases.md` | 十种异常处置表 | Agent 决策依据 |
| SKILL.md 阶段0–5 流程 | 预算纪律（≤12 调用/案例）、骨架早存、终检修复循环 ≤2 次 | Agent |
| 三段交付 + claim_source_matrix.csv | 论断清单—证据表—成稿 + 多对多矩阵 | 评分主体 |

## 余量缺口表

| 缺口 | 归属维度 | 根因 | 对应活路 | 可拿回（÷3） | 承担版本 |
|-|-|-|-|-|-|
| 题面原子指令无拆分无核验 | 任务完成度 15 + 效率 5 | B 内容 | CS1 指令清单 + 成稿审计机检 | +3 | v2.0.0 |
| 增益无实跑证据 | 质量增益 15 + 可验证性 5 | B 内容 | CS2 失败模式拦截审计产物 | +3 | v2.0.1 |
| 支撑关系只到"摘录"级，复核者仍须人工对句 | 可核验性 5 + 正确性 15 | C 增量 | SP-A 分句级 support_span 机检 | +2 | v2.0.2 |
| 成稿数值无逐值溯源机检 | 正确性 15 + 完整性 5 | C 增量 | SP-B 数值溯源（L4 跨题迁移守恒思想） | +2 | v2.0.3 |
