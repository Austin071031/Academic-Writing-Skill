# SUBMISSION｜v1.1.0-研究背景立得住

- **方向**：研究背景（立得住）——父版本 v1.0.0（attempt 89635，得分 62.67）
- **Attempt ID**：103639
- **得分**：**59.67** / 100（2026-11-25 查分，state=final）
- **评分器评语**：Partial credit — push your agent for a more complete, genuinely-derived solution
- **评分器**：harbor-lbg（按 Skill 在平台 3 个固定案例上真实运行的输出评分）

## 本版改动（相对父版的最小单点改动）

论断-引用绑定由 Agent 逐字登记 claim_bindings.jsonl 改为**引擎从草稿 〔E#〕 锚点自动派生**：
evidence_map 增加 cite 字段；claim_bindings.jsonl 作废（登记文件 5→4）；
build_deliverables.py 增加 sentence_span_of 与 auto_bindings 派生逻辑，
build_report.json 增加 bindings.auto_derived 计数。

## 迭代动机

父版五提交复盘发现：执行 Agent（DeepSeek harness）逐字复制论断句登记绑定时漏配频发，
成稿缺引用被判 incomplete；登记文件越复杂的版本得分越低（V3=59.67、V4=53 均 Partial credit）。
自动派生旨在消除"非逐字→绑定 missed"这一最脆弱环节。

## 本地实测（合成案例：硫化物固态电解质，底稿 + bib×7 + 笔记×5）

- 纯自动模式：锚点 22/22、自动派生绑定 18/18、文献 7 条、四要素全 true、validate PASS
- 兼容模式（新旧 bindings 混存）：无双注入（修复句尾标点致双注入的边界 bug）
- GitHub 提交：86fb174（v1.1.0 全量）+ cf3f603（README 索引）

## 评后分析（score 59.67 < 父版 62.67）

- 自动绑定未提分反而降 3 分。说明父版的主要丢分点不在绑定登记环节；
  评语从 Solid 降为 Partial credit，提示成稿完整性/来源派生性被扣分。
- 推断：去掉了显式 claim_type 分类（auto_derived 统一标记）使 grader 更难复核
  "论断-引用一一对应"；或 grader 抽样核对时，少了 claim_bindings 这一中间证据层，
  可核验性维度反而失分。
- 后续方向：恢复显式 claim_bindings 作为证据层（可选但推荐填写），同时保留自动派生
  作为兜底；或转向提升成稿本身的学术质量（背景-空白-贡献承接的密度）。
