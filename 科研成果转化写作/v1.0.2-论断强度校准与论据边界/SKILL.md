---
name: transfer-claim-calibration
description: 科研成果转化写作——论断强度校准与论据边界方向（说得准）。当任务要求把论文、技术报告等科研材料改写为科普文章、新闻稿、简报或申报材料，且需要保证论断强度与源文证据匹配（初步结果不得写成定论、相关不得写成因果、不得绝对化、不得新增源文外结论、不得翻转否定）时触发；为受众可读性打磨、事实数据台账、术语一致性或从头撰写论文时不触发（有专门 Skill）。产出：源文论断清单（含强度分级与因果性标注）、达标改写稿（.md）、论断强度校准报告（逐条 kept/downgraded/upgraded/negation_flip/missing/new_claim 判定与修改建议）、逐条来源映射与修改记录。
---

# 科研成果转化写作：论断强度校准与论据边界

把科研材料改写为目标文体的稿子时，保证"说得准"：每一句论断的强度与源文证据同级，
不把相关写成因果、不把初步结果写成定论、不绝对化、不编造源文没有的结论。
脚本承担全部机械核查（论断抽取、强度分级、升格/否定翻转/新增结论检测），Agent 只做判断与写作。

## 三条红线

1. 不臆造源文外的事实、数据、文献与结论；改写稿中任何论断句必须能回溯到源文论断。
2. 不臆造核验结果：`claim_engine.py check` 未通过（exit≠0）时不得声称达标，必须修复重跑或如实降级。
3. 论断强度、因果性与否定极性的改动必须走引擎核验；不得凭语感把"初步表明/有望/相关"改成"证明/将/导致"。

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

Agent 读 `/app/work/inspection.json`：确认 `audience`、`genre`、`length_limit`、`source_candidates`。若材料含 PDF，先用 `pdftotext <pdf> /app/work/source.txt` 转文本；失败则尝试 `pdftotext -layout`，再失败记入 exceptions.json 并转 Phase 5 降级交付。

## Phase 2：源文结构化与论断抽取

```bash
python3 /skills/weekly-skill/scripts/parse_source.py <源文文件...> --work /app/work
python3 /skills/weekly-skill/scripts/claim_engine.py extract --source /app/work/source.json --work /app/work
```

Agent 读 `work/source_claims.json`：每条论断含 `claim_id`、`pid`、`sentence`、`level`（L0 绝对化/L1 确立/L2 初步/L3 展望）、`causality`（因果/相关/无）、`markers`、`negated`。**改写稿中对应句的强度级别、因果性与否定极性必须与源文同级**；判据见 references/claim_rules.md。

## Phase 3：撰写改写稿

Agent 依据论断清单，把源文改写为完整、可直接使用的目标文体稿件，写入 `/app/work/rewrite_draft.md`。写作要求：

- 完整成稿（标题+正文），不是提纲、不是建议、不是片段；
- 源文的关键结论、数据、单位、样本量、图表引用、限定条件必须保留；
- **论断强度与源文同级**：L2（初步表明/提示）不得写成 L1（证明/表明）或 L0（彻底解决/所有），L3（有望/可能）不得写成必然；
- **因果性不得升格**：源文"相关/伴随/关联"不得写成"导致/促使/取决于/因而"；
- **否定极性不得翻转**：源文"未能/无法/不"在改写稿中保持否定；
- 限定条件（在…条件下、对…体系、样品量）随论断一并保留，不得悄悄扩大适用范围。

## Phase 4：对齐与论断强度核查

```bash
python3 /skills/weekly-skill/scripts/align_rewrite.py --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --work /app/work
python3 /skills/weekly-skill/scripts/claim_engine.py check --rewrite /app/work/rewrite_draft.md --work /app/work
```

Agent 读 `claim_report.json`、`claim_report.md` 与 `claim_verdicts.jsonl`：

- `critical` 问题（upgraded 强度升格 / absolute_upgrade 绝对化 / causality_upgrade 相关写成因果 / negation_flip 否定翻转 / new_claim 源外新结论）**必须修复后重跑 check**，直至 exit=0；每条问题带 rpid 定位与"回退到源文同级措辞"的修改建议；
- `warn`（missing 关键论断丢失）：补回同级措辞句子，或确系有意删除时在 change_log 写明理由；
- `info`（downgraded 更保守）：允许，但若关键结论因降格失真则恢复源文同级；
- `alignment.added`：改写新增段落若含任何结论标记而源文无对应论断，引擎已判 new_claim，必须删除或回溯源文。

同时 Agent 写三个台账文件（JSON 数组）：

- `work/evidence_map.json`：[{item_id, location(R 段号), source(源文 pid+原句), support(原文依据), rationale, verification(引擎核查结果)}]，覆盖每个数据点与关键论断；
- `work/change_log.json`：[{op, location, before, after, reason}]；
- `work/uncertainty.json`、`work/manual_confirmations.json`（如源文论断自相矛盾的处置、受众未明示的假设）。

## Phase 5：交付

```bash
cp /app/work/rewrite_draft.md /app/output/rewrite.md
cp /app/work/claim_report.md /app/output/claim_report.md
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --skill "transfer-claim-calibration v1.0.2" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output --work /app/work
```

`validate_output.py` 返回非 0 时按提示修复，或将 status 降为 partial 并写明 limits。

## 异常处置表

| 异常 | 处置 |
|-|-|
| 源文缺失/为空 | 记 exceptions.json，status=failed，写明缺什么 |
| PDF 解析失败 | 试 `-layout`/OCR 工具；仍失败则降级 partial，标注无法读取部分 |
| 源无论断句（extract 抽取 0 条） | 记 uncertainty.json：源文为纯方法/数据描述；check 仍跑（查 new_claim），正常交付 |
| 源文论断本身自相矛盾（两处同级论断互相冲突） | 不替作者裁决：两处都保留并标注，入 manual_confirmations 请人工确认 |
| 源文本身即 L0 绝对化措辞 | 改写可保留同级措辞（kept），但入 manual_confirmations 提示人工确认是否宜降格 |
| 受众/文体未指定 | 按"公众/科普文章"处理，记 manual_confirmations；论断核查不受影响 |
| 篇幅与论断保留冲突 | 优先保住关键论断与其限定条件，压缩方法与背景，在 change_log 说明取舍 |
| 引擎判 missing 但 Agent 确认对应句存在 | 句级相似度启发式漏配：改写句措辞向源文靠拢，或在 uncertainty.json 记录人工复核结论 |
| 材料不足以下笔 | 交付 partial，列缺口清单 |
| 预算过半未完成 Phase 3 | 立即跳到 Phase 5，以现有草稿交付 partial |

## 预算兜底

模型请求过半仍未完成 Phase 3：停止打磨，用当前 rewrite_draft.md 直接跑 Phase 4-5，
critical 未清零时 status=partial，在 uncertainty.json 写明"论断核查未全部通过，剩余 critical 见 claim_report.md"。
