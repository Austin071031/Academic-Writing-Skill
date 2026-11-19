---
name: transfer-fact-fidelity
description: 科研成果转化写作——事实数据保真与内容取舍台账方向（"留得住"）。当任务要求把论文、技术报告等科研材料改写为科普文章、新闻稿、简报或申报材料，且必须保证数字、百分比、样本量、单位、图表编号与源文一致、并说明每段保留/压缩/删除理由时触发；为受众可读性打磨、论断强度校准、术语统一、纯语言润色或从头撰写论文时不触发（有专门 Skill）。产出：逐值保真核验报告（含换算式）、逐段取舍台账、达标改写稿（.md）、逐条来源映射与修改记录。
---

# 科研成果转化写作：事实数据保真与取舍台账

把科研材料改写为目标文体时，保证**每个数字都能在源文中找到出处**，且**每段的保留/压缩/删除都有据可查**。脚本承担全部逐值比对（正向保真 + 反向溯源 + 图表编号 + 取舍台账校验），Agent 只做判断与写作。

## 三条红线

1. 不臆造源文外的事实、数据、文献与 DOI；改写稿出现的每个"数值+单位/百分比"都必须能在源文中 verbatim 或 derived 匹配，否则删除或由作者确认。
2. 不臆造核验结果：`fidelity_engine.py check` 判 FAIL（exit≠0）时不得声称数据保真，必须修复后重跑直至 PASS，或如实降级 status=partial 并写明 limits。
3. 数字、单位、图表编号的任何改动必须走引擎核验（含换算式），不得凭印象手改；引擎判 altered/unverified 的项必须改回源文值或删去。

## 运行环境约定

- 输入：`/input/case.json`、`/input/task.md`、材料文件（md/txt/tex/pdf/docx）。
- 中间产物：`/app/work`；最终交付：`/app/output`（含 result.json）。
- 本 Skill 安装于 `/skills/weekly-skill`，命令均用绝对路径；也可用 `$SKILL_DIR` 替换。
- 预算：64 次模型请求 / 900 秒。脚本秒级完成；把请求留给改写与判断。

## Phase 0：落盘骨架（防超时空手）

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
```

## Phase 1：解析任务与材料

```bash
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
```

Agent 读 `/app/work/inspection.json`：确认 `length_limit`（篇幅）、`source_candidates`（源文）、任务约束。若材料含 PDF，先用 `pdftotext <pdf> /app/work/source.txt` 转文本；失败则试 `pdftotext -layout`，再失败记入 exceptions.json 并转 Phase 5 降级交付。

## Phase 2：源文结构化

```bash
python3 /skills/weekly-skill/scripts/parse_source.py <源文文件...> --work /app/work
```

Agent 读 `work/source.json` 的 `fact_index`：这是后续保真核验的基准清单（number/percent/sample/figure_ref/table_ref/year/compare/conclusion，含 pid 溯源）。**写作前先浏览一遍全部事实**，知道哪些值必须保住。

## Phase 3：先写取舍决定，再写改写稿

Agent 逐段阅读源文 paragraphs，为每段写取舍决定到 `/app/work/retention_decisions.jsonl`（JSON Lines，每行一条，覆盖全部含结论/比较/关键数据的段落）：

```json
{"source_pid": "S001-P004", "action": "保留", "reason": "核心结果数据段，85.3%/62.1%/320 Ω 等数据全部保留"}
```

- `action` 只能是 `保留`（内容基本全留）/ `压缩`（删冗余留要点）/ `删除`（整段不进入改写稿）；
- `reason` 必填；**删除决定理由不得为空或敷衍**（引擎要求 ≥4 字且不得为"无/无理由"等），删除含关键数据的段落必须在理由中说明为什么这些数据可以丢（如"与主线无关的次要表征数据"）；
- 决定先于成稿：先想清楚每段去哪，再动笔，可避免"无意丢数据"。

然后依据决定与篇幅约束撰写完整改写稿 `/app/work/rewrite_draft.md`：

- 完整成稿（标题+正文），不是提纲、不是建议、不是片段；
- fact_index 中 number/percent/sample/figure_ref/table_ref 事实原则上必须出现；篇幅不够时优先保 compare/conclusion 同段的关键数据，其余缺失项须在 retention_decisions 的 reason 中说明；
- 允许单位等价与换算（5 nm ↔ 5 纳米 ↔ 0.005 μm；85.3% ↔ 0.853；73.4% ↔ 73%），引擎会按判据自动认可并在报告中写换算式；
- 论断强度与源文一致；不得引入源文外的任何数值。

## Phase 4：对齐、保真核验与台账校验

```bash
python3 /skills/weekly-skill/scripts/align_rewrite.py --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --work /app/work
python3 /skills/weekly-skill/scripts/fidelity_engine.py check --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --work /app/work
python3 /skills/weekly-skill/scripts/fidelity_engine.py ledger --decisions /app/work/retention_decisions.jsonl --work /app/work
```

Agent 读 `fidelity_report.json` 与 `retention_ledger.json`：

- `critical` 问题（altered 篡改值、unverified 源外新数值、unknown 图表编号、关键数据 missing）**必须修复后重跑 check**，直至 exit=0；
- `warn` 问题（非关键数据 missing、源文图表引用消失）逐条处置：补回，或在 retention_decisions 的 reason 与 change_log 中写明取舍理由；
- ledger 报 missing_decision / unreasoned_action 时，补齐 retention_decisions.jsonl 后重跑 ledger，直至 exit=0；
- `alignment.dropped`：源文段落未被覆盖——与 retention_decisions 对照，有"删除"决定则一致，否则补写决定；
- `alignment.added`：改写新增段落——确认只是过渡句，若含任何源文外数值，check 会判 unverified，必须删除。

同时 Agent 写四个台账文件（JSON 数组）：

- `work/evidence_map.json`：[{item_id, location(R 段号), source(源文 pid+原句), support(原文依据), rationale, verification(引擎核查结果)}]，覆盖每个数据点与关键论断；
- `work/change_log.json`：[{op(改写/压缩/删除/新增), location, before, after, reason}]；
- `work/uncertainty.json`、`work/manual_confirmations.json`（如被删数据的必要性质疑、待作者确认项）。

## Phase 5：交付

```bash
cp /app/work/rewrite_draft.md /app/output/rewrite.md
cp /app/work/fidelity_report.md /app/output/fidelity_report.md
cp /app/work/retention_ledger.md /app/output/retention_ledger.md
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --skill "transfer-fact-fidelity v1.0.1" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output --work /app/work
```

`validate_output.py` 返回非 0 时按提示修复，或将 status 降为 partial 并写明 limits。

## 异常处置表

| 异常 | 处置 |
|-|-|
| 源文缺失/为空 | 记 exceptions.json，status=failed，写明缺什么 |
| PDF 解析失败 | 试 `-layout`/OCR 工具；仍失败则降级 partial，标注无法读取部分 |
| fact_index 为空（源文无检出事实） | check 退化为纯反向 unverified 扫描；缺失风险入 manual_confirmations |
| 篇幅与内容冲突（关键数据放不进） | 优先保 compare/conclusion 同段数据；其余缺失在 retention_decisions reason 说明，check 会按 warn 放行 |
| 源文数据自相矛盾 | 不替作者裁决：两处都保留并标注，入 manual_confirmations |
| 单位不在换算表（如 MPa·√m） | 引擎只做原样比对；确需换算时在 evidence_map 写明算式，入 manual_confirmations 待作者确认 |
| 改写稿引用了源文没有的图/表编号 | critical：删除该引用或确认是笔误，入 manual_confirmations |
| 改写稿出现源文没有的年份/版本号 | 已被遮蔽规则跳过，不判 unverified；若是实质性新事实仍须人工确认 |
| 材料不足以下笔 | 交付 partial，列缺口清单 |
| 预算过半未完成 Phase 3 | 立即跳到 Phase 5，以现有草稿与已写的决定跑 Phase 4-5，status=partial |

## 预算兜底

模型请求过半仍未完成 Phase 3：停止打磨，用当前 rewrite_draft.md 与 retention_decisions.jsonl 直接跑 Phase 4-5，
status=partial，在 uncertainty.json 写明"未完成取舍台账/保真修复"。
