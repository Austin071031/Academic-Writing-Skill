---
name: evidence-strength-calibrator
description: 文献证据驱动写作之证据强度 Skill。当任务要求评估论断的证据等级、按研究设计与样本量给证据分级、校准学术表述强度、避免把弱证据写成强结论时使用。典型触发：给定材料要求“评估证据强度”“给论断分级”“把结论写保守/写实”“检查是否有过度推断”“按证据等级改写结论”。不做的事：无材料臆断等级、替代同行评议做决定。流程：脚本预检→四维分级（rubric见references/rubric.md）→分级理由表→分级-措辞对照校准成稿→脚本扫描不相容表述→契约化result.json。
---

# evidence-strength-calibrator：证据分级与措辞校准

每一步都要能回答：**分得级**（研究设计/样本量/重复验证/一致性四维定级，理由可复核）、**对得上话**（成稿动词与证据级别相容，脚本机检强动词×弱分级）、**不拔高**（单篇小样本不写成品领域共识，相关不写成因果）、**降得下来**（冲突与局限如实呈现）。

重型机械（案例解析、材料文本化、逐字核验、契约回填、一致性终检）全部由自带脚本完成；
Agent 的职责是**做判定与写作决策、审阅脚本报告、诚实标注**，不是凭记忆引用文献、不是整段无来源重写。

## 何时调用 / 何时不调用

- **调用**：题面属于“证据强度”类文献证据驱动写作任务，且要求交付带来源/证据定位的写作产物。
- **不调用**：纯内容问答、无材料的事实补全、与证据来源无关的排版美化任务；此时直接完成题面要求，不得套用本流程产物。
- 不确定时：先完成阶段1任务解析，把判断依据写入 task_profile.json 的 assumptions。

## 输入与产物

输入：`/input/case.json`（含 `case_id` 与 `output_contract`）、`/input/task.md`、材料文件（PDF/文本等，由预检报告给出清单与可读性）。

产物（全部写入 `/app/output`，可直接编辑与继续修改）：

| 产物 | 文件 | 说明 |
|-|-|-|
| 论断清单 | `claims.jsonl` | 原子论断单元：编号、文本、状态、证据引用 |
| 证据表 | `evidence.csv` | 逐字摘录 + 文档/页码定位 + 类型/关系/强度 |
| 成稿 | `draft.md` | 满足题面体裁受众格式，句末标注 [claim_id] |
| 分级理由表 | `strength_rationale.csv` | 每条论断四维判定依据与级别（主交付） |
| 结构化结果 | `result.json` | `case_id` + output_contract 全字段 + status + 假设/不确定性/变更/异常 |

## 依赖与环境自适应

仅依赖 Python 3.8+ 标准库；PDF 提取依次尝试 pdftotext / PyMuPDF / pypdf，全部失败如实记录 failed，
**不生成缺文文本冒充成功**。离线环境：一切需要联网的核验给可回查路径并标 offline_unverified。

## 执行流程

`<SKILL>` 为 Skill 安装目录（评测时为 `/skills/weekly-skill`）。
预算：64 次模型请求 / 900 秒 / 每次响应 ≤16384 token（含推理）。脚本合计 <30 秒；模型调用目标 ≤12 次/案例。
**任何时刻中断，/app/output 里已有 result.json 骨架与已完成产物。**

### 阶段0 预检（0 次模型调用）

```bash
bash <SKILL>/scripts/run_pipeline.sh /input /app/work /app/output
```

读取 `/app/work/brief.json`（case_id、output_contract 键清单、输入文件盘点、issues）与
`/app/work/text_manifest.json`（每个材料的文本化状态、引擎、失败原因）。任何 failed 文档原样转入
result.json 的 `exceptions`；**不得假设材料内容，一律读真实文件**。

### 阶段1 任务解析与材料画像（≤1 次模型调用）

填写 `/app/work/task_profile.json`：
```json
{"task_verb": "生成|改写|校对|结构化|核验", "audience": "题面指定受众，未指定时注明假设",
 "genre": "题面指定体裁", "output_contract_reading": "逐字段抄录 output_contract 的键与预期类型",
 "assumptions": ["题面未说明而自行假定的项"], "open_questions": ["材料不足/冲突、需人工确认的问题"]}
```
契约字段语义不明 → 按最保守解释填，理由写入 assumptions。

### 阶段2 四维证据分级（≤2 次模型调用）

对每条论断按 references/rubric.md 的四维口径定级 A/B/C/D，写入 /app/output/strength_rationale.csv：
列：claim_id,study_design,sample_size,replication,consistency,strength,rationale。
rationale 必须写出可复核的理由（如“单项回顾性研究，n=32，无外部重复”），不允许只填级别。证据充分但外部一致性未知时级别就低不就高。claims.jsonl 同步回填 strength。

### 阶段3 措辞校准（≤2 次模型调用）

按分级—措辞对照表写 draft.md，每句动词与论断级别相容：
A→证实/表明/一致表明；B→表明/显示；C→提示/初步表明/可能相关；D→个案提示/尚无定论/有待验证。
C/D 级论断禁用：证明、证实、公认、普遍认为、确定有效、根治、消除。相关性证据禁用因果动词（导致/引起/决定）。单篇研究禁用共识性表述。
脚本 R7 会机检“弱分级×强动词”，命中必须改写或在 uncertainty 说明理由。

### 阶段4 成稿组装（≤2 次模型调用）

按 case.json 指定体裁、受众与格式写 `/app/output/draft.md`：每个实质性论断句末标注 `[claim_id]`；
unsupported 论断不进成稿（列入 out_of_scope 并说明）；引用编号与参考文献表逐一对应；
修改类任务须附修改差异说明（change_log）。

### 阶段5 终检与回填（0 次 + ≤2 次修复）

```bash
python3 <SKILL>/scripts/validate_output.py /input /app/work /app/output <SKILL>
```

脚本校验 R1–R7（契约字段覆盖、三段产物齐备、结构合法、**摘录逐字命中**、成稿覆盖论断、方向专属检查），
写 `validation_report.json` 并回写 result.json 的 status。**报告中的 error 必须修复或在 uncertainty 中给出诚实说明**；
修复循环最多 2 次，仍不通过则以 partial 交付，禁止为凑 success 删改问题记录。

## 通用异常处置（所有方向共用）

| 情形 | 处置 |
|-|-|
| 材料文件缺失或不可读 | 记入 exceptions；相关论断标 unsupported 或 out_of_scope；result.json status 降档 |
| PDF 转换失败（扫描版/加密/损坏） | 在 text_manifest.json 记 failed 与原错误；该文档全部摘录标 needs_ocr 或 exclusion_reason，不臆造内容 |
| 仅有摘要、无全文 | 摘录 doc_type 记 abstract_only；摘要性论断强度上限 C；所有依据摘要的表述必须写"摘要显示"而非"原文证明" |
| 原文与摘要矛盾 | 以全文为准；矛盾本身记入 uncertainty 与 change_log，成稿处加限定语并指向证据表 |
| 证据相互冲突 | 双方证据都登记（support_type=conflicting）；成稿并陈双方并加限定语；不得只取有利一方 |
| 材料不足以下任何结论 | 论断标 unsupported，写入 open_questions（人工确认项），不补造事实 |
| output_contract 字段语义不明 | 按最保守解释填写并在 assumptions 说明；字段名一个不改 |
| 单次响应接近 16384 token 上限 | 分片写文件（每次追加一段），禁止一次输出整份大表 |
| 预算将尽（>56 次请求或 >800 秒） | 立即跑 validate_output.py，把当前最优产物定格为 result.json，status 如实标 partial |
| 需要联网才能完成的核验 | 不伪造联网结果；给可回查路径（DOI/Crossref/出版社检索式）并标 offline_unverified |


## 完成自查清单（提交 result.json 前逐项确认）

1. result.json 含 case_id 与 output_contract 全部字段（脚本 R1 无 missing）；
2. claims.jsonl / evidence.csv / draft.md 齐备，论断编号在成稿中可逐条回溯；
3. 每条摘录经脚本逐字命中（validation_report.json 的 quote_verification），未命中已修复；
4. unsupported / conflicting / out_of_scope 论断均有处置说明，无补造引用；
5. assumptions / uncertainty / change_log / exceptions 如实填写，status 与实际完成度一致；
6. 全部产物为本次运行基于真实材料生成，未使用任何预制答案。

## 维护

- 版本：v1.0.3（玻尔产品周赛第四期 写作05｜文献证据驱动写作，证据强度方向）
- 强度分级口径、词表与判定规则见 references/rubric.md；输出格式见 references/output_spec.md。
