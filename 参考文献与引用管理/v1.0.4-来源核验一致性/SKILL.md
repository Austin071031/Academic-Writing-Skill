---
name: citation-verification-audit
description: 来源核验与一致性检查 Skill（条目级真实性体检 + 论断级引用匹配两层核验）。当任务要求核验参考文献是否真实/是否编造、检查正文引用与所引文献是否对得上、审计引用编号一致性，或交付"参考文献体检报告 / 引用匹配核验报告 / 带 ⚠ 标注的审校稿"时使用。典型触发：给出稿件与文献库（bib/ris/enw/csv/json/GB-T 文本），要求"检查这些文献是不是编造的""核对每处引用是否真的支持正文论断""审查引用与文献是否一致"。不做的事：不负责重排/重编引用编号（那是v1.0.1）、不负责去重合并（v1.0.2）、不负责按某样式重著录（v1.0.0）——本 Skill 只回答"文献像不像真的"与"引用对不对得上"，可与其他版本串联。产物：/app/output 下 verification_report.json（机读）、verification_report.md（人读）、annotated_manuscript.md（证据不足/不匹配句带 ⚠ 标注的可编辑稿）、evidence_map.json 与含 case_id、output_contract 全字段的 result.json。默认离线可运行；加 --online 可逐条 DOI 联网核验 Crossref（5 秒超时，失败诚实记 unverified_offline）。
---

# citation-verification-audit：来源核验与一致性检查（对得上）

两层核验，一条主线：**条目像不像真的**（引擎做确定性体检）× **引用对不对得上**（Agent 逐句裁决、引擎汇总留痕）。

- 引擎承担全部机械劳动：DOI 语法/年份/字段自洽/重复录入体检、可选 Crossref 联网比对、
  裁决覆盖率审计、编号一致性联动（cite_engine audit）、报告与标注稿生成。
- Agent 只做判断：逐句读"正文论断 ↔ 所引文献条目"，写 match_verdicts.jsonl 四档裁决。
- 每一步都诚实：本地体检只报"疑似"，不声称确证造假；离线就写 unverified_offline，绝不假装联网成功。

## 何时调用 / 何时不调用

- **调用**：任务含"核验/查证参考文献真实性、检查编造引用、核对引用与论断匹配、引用审计"等动词。
- **不调用**：任务要求改编号、去重、重著录格式——本 Skill 不改稿件编号与文献表，只体检与标注。
- 不确定时：照常跑 Phase 0–1，把判断依据写入 work/inspection.json 的 issues 并在报告说明。

## 输入与产物

输入：`/input/case.json`（case_id + output_contract）、`/input/task.md`、材料文件（稿件 md/txt/tex/docx/pdf；文献库 bib/ris/enw/ciw/csv/json/GB-T 文本）。

产物（写入 `/app/output`，均可直接编辑）：

| 产物 | 文件 | 说明 |
|-|-|-|
| 机读核验报告 | `verification_report.json` | 逐条目体检+联网状态、逐论断裁决、覆盖审计、编号一致性 |
| 人读核验报告 | `verification_report.md` | 可疑条目表、不匹配论断表、证据不足清单、总体结论 |
| 标注审校稿 | `annotated_manuscript.md` | 在不匹配/证据不足论断句后插 `<!-- ⚠ verdict: ... -->`，原文可编辑 |
| 一致性体检 | `consistency_audit.json` | cite_engine audit：越界/缺口/样式混杂 |
| 预览 | `preview.html`（尽力 `preview.pdf`） | 由 render_previews.py 生成 |
| 结构化结果 | `result.json` | case_id、output_contract 全字段、evidence_map、uncertainty、exceptions |

中间产物（work/ 下，Agent 可写）：`match_verdicts.jsonl`（Agent 裁决）、`evidence_map.json`、`stats.json`、`uncertainty.json`、`exceptions.json`、`consistency_audit.json`。

## 三条红线

1. **不臆造文献、不臆造元数据**：只能依据材料内条目字段与正文句子；不得凭记忆补全"真实的"刊名/卷期/DOI。
2. **不臆造核验结果**：离线运行如实写 `unverified_offline`/`not_attempted_offline_mode`；
   本地体检 verdict 只有 verified_internal/suspicious/insufficient_metadata，suspicious ≠ 确证造假。
3. **编号一致性只报告、不改号**：audit 发现的越界/缺口写入报告，严禁手工改稿件里的编号数字
   （如需修复编号，转v1.0.1的 renumber 流程，不在本 Skill 内执行）。

## 执行流程

`<SKILL>` = `/skills/weekly-skill`（本 Skill 安装目录）。预算：64 次模型请求 / 900 秒 / 每次响应 ≤16384 token。
脚本合计 <30 秒（联网模式按 DOI 数 ×5s 上限）；模型调用目标 ≤10 次/案例。
**任何时刻中断，/app/output 已有 result.json 骨架与已完成产物。**

### Phase 0 预检（0 次模型调用）

```bash
python3 <SKILL>/scripts/init_result.py --case /input/case.json --out /app/output
python3 <SKILL>/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
```

读 `/app/work/inspection.json`：确认 `manuscript_candidates` 与 `library_candidates` 非空；
若有 issues，全部转入后续 uncertainty。

### Phase 1 解析材料（0 次模型调用）

```bash
python3 <SKILL>/scripts/parse_manuscript.py <稿件路径> --work /app/work
python3 <SKILL>/scripts/parse_library.py <文献库文件...> --work /app/work
```

（路径从 inspection.json 的 candidates 取；多文献库文件全部传入。）

### Phase 2 逐句裁决（Agent，核心判断，目标 ≤6 次模型调用）

读 `/app/work/manuscript.json` 与 `/app/work/library.json`。找出**全部带引用标记的正文段落**
（kind=body 且 cite_marks 非空），逐句做"正文论断—所引文献"主题匹配裁决，写
`/app/work/match_verdicts.jsonl`（JSONL，每行一条，覆盖每个带引用段落的每个论断句）：

```json
{"pid": "P002", "sentence": "硅在嵌脱锂过程中体积变化超过 300%", "entry_ids": ["R004"], "verdict": "supports", "rationale": "条目题名 'Volume Expansion of Silicon Electrodes' 与论断的'体积变化超过300%'直接对应"}
```

- `entry_ids` 用 library.json 里的 R 编号（如 "R004"），按该句引用标记 [n] 对应的文献表顺序映射。
- verdict 四档：`supports`（条目主题直接支撑论断）/ `partially`（相关但只支撑部分，如支撑机理不支撑数值）/
  `unrelated`（条目主题与论断对不上）/ `insufficient_evidence`（材料内信息不足以判断）。
- **裁决规则**（详见 references/verdict_rubric.md）：
  1. 只依据材料内信息：条目 title/venue/year/字段 + 正文论断句；条目有 abstract 字段时可用。
  2. 材料不足 → 必须判 `insufficient_evidence`，并在 rationale 写明**缺什么**（如"条目仅题名，无摘要，无法确认是否报道300%膨胀"）。
  3. **不得凭记忆断言文献真伪**——记忆可能错；条目是否真实由引擎体检回答，Agent 只判"对得上与否"。
  4. rationale 必须引用双方原文短语（论断句片段 + 条目字段片段），空 rationale 会被引擎审计记 issue。
- 判据与每档 3 例：references/verdict_rubric.md；疑似编造条目特征：references/fabrication_heuristics.md。

### Phase 3 引擎汇总（0 次模型调用）

```bash
python3 <SKILL>/scripts/verify_engine.py --library /app/work/library.json --manuscript /app/work/manuscript.json --verdicts /app/work/match_verdicts.jsonl --work /app/work --out /app/output
```

可选联网（逐条 DOI 请求 Crossref，5 秒超时，失败诚实降级）：

```bash
python3 <SKILL>/scripts/verify_engine.py ... --online
```

引擎产出：verification_report.json/md、annotated_manuscript.md（⚠ 标注）、work/evidence_map.json、
consistency_audit.json（编号连续性并入报告）。**缺漏审计**：Phase 2 漏判的带引用段落会在报告
"裁决覆盖审计"列出，并在标注稿中插 `⚠ 缺裁决` 注释——此时必须回 Phase 2 补齐后重跑 Phase 3，
模型请求过半则按"预算兜底"直接交付 partial。

### Phase 4 组装（0 次模型调用）

```bash
python3 <SKILL>/scripts/assemble_result.py --work /app/work --out /app/output --skill "citation-verification-audit v5.0.0" --status success
```

裁决有缺漏或材料不全致部分段落无法判 → `--status partial`（诚实降级，validator 只作 WARN）。

### Phase 5 终检与预览（0 次模型调用）

```bash
python3 <SKILL>/scripts/validate_output.py --out /app/output
python3 <SKILL>/scripts/render_previews.py --out /app/output
```

## 异常处置表

| 异常 | 处置 |
|---|---|
| 字段缺失（无 DOI/年份/刊名） | 该体检项记 insufficient_metadata；不脑补。计入 uncertainty.json |
| DOI 解析失败/含非法字符 | doi_syntax 记 suspicious（evidence 写明原因）；联网跳过该条，记 online_skipped_invalid_doi |
| 条目歧义（同名不同文） | 按材料内字段裁决；无法区分 → insufficient_evidence，rationale 写明歧义点 |
| 编号冲突/越界/缺口 | cite_engine audit 写入 consistency 节；**只报告不改号**（红线3） |
| 不支持的稿件/文献库格式 | inspect_case 会标注；解析失败则该文件记 exceptions.json，其余材料照常核验 |
| 文件损坏/无法解码 | parse_* 如实记 issues；能解析多少核验多少，status=partial |
| 文献库为空 | 全部论断裁决记 insufficient_evidence（无条目可对照）；报告结论 issues_found，写明原因 |
| 超时/网络不可用 | --online 模式逐条 try+timeout=5s，失败记 unverified_offline；默认离线模式不受影响 |
| match_verdicts.jsonl 缺失/坏行 | 引擎审计记 verdicts_missing/verdict_bad_json；缺失段落标注 ⚠ 缺裁决，status=partial |

## 预算兜底

若模型请求过半仍未完成 Phase 2：立即对剩余带引用段落批量写
`{"verdict": "insufficient_evidence", "rationale": "【预算兜底】剩余段落未逐句裁决，证据不足，需人工复核"}`，
跑 Phase 3–5 交付 `status=partial`。绝不为省请求而漏跑引擎或虚报 supports。
