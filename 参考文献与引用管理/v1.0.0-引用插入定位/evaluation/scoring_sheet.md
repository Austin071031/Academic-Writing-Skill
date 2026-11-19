# scoring_sheet.md — v1.0.0 自查评分表（100 分制）

对照竞赛评分维度自查。每项给证据（文件路径 / 命令输出），无证据不得分。

## 一、实际效果（40）

| 项 | 分 | 判定标准 | 证据 |
|---|---|---|---|
| 任务完成度 | /15 | edited_manuscript.md 中每个该引的论断句末都有标记；references.md 收录全部被引条目；result.json 含 output_contract 全部字段 | edited_manuscript.md / result.json |
| 正确性 | /15 | 标记紧贴论断句末（非段末）；编号 1..N 连续且与文献表一一对应；未给作者新结果/公知常识加引用；无臆造条目 | placement_audit.json / cite_engine audit |
| 完整性 | /5 | 段落结构与标题保留；一句多引合并、多句一引展开均正确；异常全部记录 | placement_audit.json / exceptions.json |
| 可核验性 | /5 | evidence_map 每条含 claim_id+entry_id+location+rationale；change_log 覆盖每次插入/剥除 | result.json 内字段 |

## 二、使用增益（25）

| 项 | 分 | 判定标准 |
|---|---|---|
| 质量 | /15 | 相对基础 Agent：无段末堆放、无编号错位、无虚假溯源（对照 failure_modes.md 逐条核） |
| 效率 | /5 | Agent 模型请求主要用于 Phase 3 判断；机械劳动零模型开销（脚本秒级完成） |
| 可验证 | /5 | validate_output.py PASS；placement_audit 与 references.json 可独立复检 |

## 三、创新增益（15）

| 项 | 分 | 判定标准 |
|---|---|---|
| 新能力 | /5 | 论断级（句子级）引用定位，而非段落级堆放——基础 Agent 不具备的稳定能力 |
| 方法 | /5 | Agent 判断（claim rubric）与确定性引擎（定位/插入/重排/渲染/审计）职责分离；三级句子定位容错 |
| 证据 | /5 | worked_example.md 端到端可复现；placement_audit 双向错放审计数据 |

## 四、可靠体验（10）

| 项 | 分 | 判定标准 |
|---|---|---|
| 易用 | /3 | SKILL.md Phase 0-5 逐字命令可直接复制执行 |
| 稳定 | /4 | 合成案例端到端 PASS；重复运行结果一致（幂等，引擎无随机性） |
| 异常 | /3 | 异常表 10 类场景均有降级路径；定位失败跳过不臆造；partial 诚实标注 |

## 五、生态贡献（10）

| 项 | 分 | 判定标准 |
|---|---|---|
| 文档 | /3 | README/USAGE/CHANGELOG/references 四件套齐全且互相一致 |
| 可复用 | /4 | 共享核心 8 脚本接口未改；decisions JSONL 契约与 SPEC-common 一致，可被其他版本/工具复用 |
| 分享 | /3 | GITHUB_URL.txt 一行有效仓库地址 |

## 自测基线（合成案例 SYNTH-01，实测）

- 5 条 decisions（含 1 条故意失败）→ 插入 4 标记，编号 1-5 连续，异常 1 条如实记录；
- 原稿段末堆放疑似 2 处被审计捕获，插入后错放 0；
- `validate_output.py` 输出 `PASS (status=success)`，exit 0。
- 自评：一 40/40（合成案例范围内全部满足）；其余维度按上表逐项对照打分。
