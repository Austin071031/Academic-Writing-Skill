---
name: citation-verifier
description: 文献证据驱动写作之引用准确性 Skill。当任务要求校验参考文献真实性、著录信息、文内引用编号与参考文献表一致性、识别二手转引/撤稿/版本差异，或要求为引用给出可回查核验路径时使用。典型触发：给定稿件与文献库要求“核对参考文献”“检查引用编号是否对应”“验证每条引用是否真实支持正文说法”“整理可回查的引用核验表”。不做的事：联网代查（环境离线时只给核验路径）、无引用材料时的著录补全臆造。流程：脚本预检→引用清点建登记→三方一致性核验（编号/著录/逐字支持）→二手转引与版本差异识别→引用核验表与契约化result.json。
---

# citation-verifier：引用真实性、著录与编号一致性核验

每一步都要能回答：**编号对得上**（文内引用、参考文献表、论断映射三方一致）、**著录查得全**（作者/年/题名/出处/卷期页/DOI 缺项即报）、**支持对得上原文**（每条被引论断有逐字摘录且机检命中）、**边界诚实**（离线不能联网核验就给出可回查路径并标注，绝不声称已核）。

重型机械（案例解析、材料文本化、逐字核验、契约回填、一致性终检）全部由自带脚本完成；
Agent 的职责是**做判定与写作决策、审阅脚本报告、诚实标注**，不是凭记忆引用文献、不是整段无来源重写。

## 何时调用 / 何时不调用

- **调用**：题面属于“引用准确性”类文献证据驱动写作任务，且要求交付带来源/证据定位的写作产物。
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
| 参考文献登记 | `reference_registry.json` | 全部引用编号、著录字段完整性、版本信息 |
| 引用核验表 | `citation_audit.csv` | 每条引用的三方核验结论与可回查路径（主交付） |
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

### 阶段2 引用清点与登记（≤2 次模型调用）

从底稿与材料中提取全部文内引用（编号或作者-年）与参考文献表，建立 /app/output/reference_registry.json：
```json
{"references": [{"ref_id": "R01", "in_text": true, "in_list": true,
  "fields": {"authors": "", "year": "", "title": "", "venue": "", "volume_issue_pages": "", "doi": ""},
  "missing_fields": ["doi"], "version_note": "正式发表/预印本/材料未说明"}]}
```
materials 中找不到全文的被引文献记 in_library=false（无法逐字支持核验）。

### 阶段3 三方核验（≤3 次模型调用）

写入 /app/output/citation_audit.csv，每条引用一行，逐列核验：
1. 编号一致：文内出现 ↔ 文献表在列，双向缺失都记 error；
2. 著录完整：缺字段列入 missing_fields；同一文献在材料中出现多个版本（预印本/正式）记入 version_note；
3. 逐字支持：该引用支撑的论断必须挂 evidence.csv 摘录且经脚本 R5 在原文命中；命中失败即 error（引了但不支持或支撑了别的句子）；
4. 二手转引：摘录或著录中出现“as cited in/转引自/见某某引”即标 secondary=true，该证据降级 background；
5. 可回查路径：verification_path 给出 DOI 链接或检索式（如 https://doi.org/<doi> 或 "Crossref 查询: 题名+第一作者"）；
   离线环境一律在 verification_status 标 offline_unverified，**禁止声称已联网确认真实性或撤稿状态**。
撤稿信息仅当材料本身提供时才记录，否则写入 open_questions。

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

- 版本：v1.0.2（玻尔产品周赛第四期 写作05｜文献证据驱动写作，引用准确性方向）
- 强度分级口径、词表与判定规则见 references/rubric.md；输出格式见 references/output_spec.md。
