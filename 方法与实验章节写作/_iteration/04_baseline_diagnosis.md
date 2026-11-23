# 阶段 4 · 基线诊断

## 基线判定

§0-9=自动（取台账最高分）：台账 5 版全部无分（evaluation_error，platform_verified）。
**最高分 ≥ 目标×0.7 不成立 → 契约层问题，禁止方向迭代，只出修复版。**
内容基线取 v1.0.0–v1.0.3 四个方向原样（不增不减），打包层重做。

## 机制资产清单（白名单，逐项功能）

| 资产 | 功能 | 读取方 |
|-|-|-|
| init_result.py | 先落 result.json 骨架（case_id、output_contract_fields） | Agent Phase 0 |
| inspect_case.py | 材料分类清点 + PDF 按页文本化 + sha256 头 + 异常登记 | Agent Phase 1 → inspection.json |
| extract_evidence.py | 11 类要素候选正则抽取 + 同名参数值索引 | Agent Phase 1 → evidence_candidates.jsonl |
| build_deliverables.py | 七节装配 + 锚点解析 + 三附录 + result.json 组装 | Agent Phase 4 |
| validate_output.py | 发布闸门（契约字段/产物存在/覆盖/锚点/占位符） | Agent Phase 4 |
| render_previews.py | 章节预览渲染（pandoc 降级 txt） | Agent Phase 4 |
| 方向引擎×4 | audit_provenance / element_matrix / repro_gate / cross_source_check | 各版 Phase 4 |
| SKILL.md 流程 | Phase 0–5 + 三条红线 + 异常处置表 | 评测 Agent |
| references 三模板 | 六要素清单/参数表/缺口追问 | Agent Phase 2–3 |

## 余量缺口表

| 缺口 | 归属维度 | 根因 | 对应活路 | 可拿回 | 承担版本 |
|-|-|-|-|-|-|
| 打包文本文件 ~68–80 > 50 | 全部（弃权） | A 弃权型 | 精简打包：去 submission/ 镜像、合并文档/参考、唯一数 ≤16 | 全部分数（0→出分区） | v2.0.0–v2.0.3 |
| 间歇性 replay 故障 | — | 平台 | 重投对冲（失败不占配额） | 同上 | 同上 |
| （方向层缺口） | 待出分后评估 | C 增量 | 待 v2 出分后按 §2.2 重算 W 再定 | — | v2.1+ |
