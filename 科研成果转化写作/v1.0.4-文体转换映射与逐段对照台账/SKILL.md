---
name: transfer-genre-ledger
description: 科研成果转化写作——文体转换映射与逐段对照台账方向（接得住）。当任务要求把论文、技术报告等科研材料转换为科普文章、新闻通稿、项目申报材料或简报等目标文体，并要求保持结构要素与论断强度对应、交付原作者可逐段复核的对照台账时触发；为事实保留核验、受众可读性适配、术语一致性或纯语言润色时不触发（有专门 Skill）。产出：文体要素映射表（genre_mapping.json）、完整改写稿（.md）、逐段对照台账（change_ledger.json + traceability_report.md，覆盖每个源文段落的去向与每个改写段落的来源）。
---

# 科研成果转化写作：文体转换映射与逐段对照台账

把科研材料按目标文体的结构模板重组改写，同时让原作者能逐段复核：每个源文段落去了哪里（保留/压缩/改写/删除）、每个改写段落来自哪里（哪个源文段落/新增过渡）、每处改动为什么。脚本承担全部机械核查（要素映射、对齐、台账生成），Agent 只做判断与写作。

## 三条红线

1. 不臆造源文外的事实、数据、引语与出处：文体模板要素在源文中无支撑内容时，必须在成稿相应位置标注「源文未提供」，严禁为凑齐文体结构而编造（尤其引语、联系方式、预期指标）。
2. 不臆造核验结果：`genre_engine.py ledger` 未通过（exit≠0）时不得声称"全程可追溯"，必须修复 critical（补上删除理由或恢复内容）后重跑，或如实降级。
3. 数字、单位、图表编号必须与源文逐值一致；新增段落凡含数值+单位，引擎会提示核对——必须确认其来自源文，否则删除或标注待确认，不得凭印象保留。

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

Agent 读 `/app/work/inspection.json`：确认 `genre`（目标文体）、`audience`（受众）、`length_limit`（篇幅）、`source_candidates`（源文）。若材料含 PDF，先用 `pdftotext <pdf> /app/work/source.txt` 转文本；失败则尝试 `pdftotext -layout`，再失败记入 exceptions.json 并转 Phase 5 降级交付。

## Phase 2：源文结构化与文体要素映射

```bash
python3 /skills/weekly-skill/scripts/parse_source.py <源文文件...> --work /app/work
python3 /skills/weekly-skill/scripts/genre_engine.py map --inspection /app/work/inspection.json --source /app/work/source.json --work /app/work
```

Agent 读 `/app/work/genre_mapping.json`：

- `genre` / `genre_recognized`：识别出的目标文体；`genre_recognized=false` 表示未识别、已按默认「科普文章」处理，处置假设已写入 manual_confirmations，需人工确认。
- `template`：目标文体的要素清单与写作要点（与 references/genre_templates.md 一致）。
- `mapping`：要素 → [源文 pid]，即每个要素可以用源文哪些段落支撑。
- `missing_elements`：源文无对应内容的要素。**写作时这些要素不得编造**，在成稿相应位置标注「源文未提供」（联系方式等占位要素写占位符）。

## Phase 3：撰写改写稿并逐段记录理由

Agent 依据 genre_mapping.json，把源文按模板要素顺序重组改写为完整、可直接使用的目标文体稿件，写入 `/app/work/rewrite_draft.md`。写作要求：

- 完整成稿（标题+正文，按模板要素组织结构），不是提纲、不是建议、不是片段；
- 源文的关键结论、数据、单位、样本量、图表引用、限定条件必须保留；删掉的是冗余不是证据；
- 论断强度与源文一致（初步结果不得写成定论，「有望」不得写成「已经」，相关不得写成因果）；
- `missing_elements` 中的要素标注「源文未提供」，不得编造。

**同时逐段撰写** `/app/work/change_reasons.jsonl`（每行一条 JSON）：

```jsonl
{"rpid":"R002","source_pid":"S001-P003","action":"改写","reason":"压缩方法细节为一句，保留 5 nm 包覆层数据"}
{"rpid":"R006","action":"新增-过渡","reason":"承上启下的背景过渡句，不含源文外事实"}
{"source_pid":"S001-P007","action":"删除","reason":"与 S001-P004 内容重复的背景句"}
```

- `action` 取值：`保留 | 压缩 | 改写 | 新增-过渡`（改写段落用）或 `删除`（源文段落用）；
- **每个改写段落**都要有一条理由；**每个被删除的源文段落**都要有一条「删除」理由；
- rpid 为改写稿段落按空行分块的序号（R001 起，与 align_rewrite 一致），source_pid 为 source.json 的段落号。

## Phase 4：对齐与台账核查

```bash
python3 /skills/weekly-skill/scripts/align_rewrite.py --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --work /app/work
python3 /skills/weekly-skill/scripts/genre_engine.py ledger --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --reasons /app/work/change_reasons.jsonl --work /app/work
```

Agent 读 `change_ledger.json` 与 `traceability_report.md`：

- `critical`（`dropped_without_reason`：源文段落被删除且无理由）**必须修复**：要么在 change_reasons.jsonl 补「删除」理由并确认删除的是冗余，要么把内容补回改写稿；修复后**重跑 ledger 直至 exit=0**；
- `warn` 逐条处置：`added_without_reason`（新增段落未标「新增-过渡」）补理由或删除该段；`added_contains_number`（新增段落含数值）核对是否源外事实；`action_contradiction`（理由动作与引擎对齐矛盾）核实是否事实漂移或理由笔误；
- 检查 `traceability_report.md` 两张表：源文段落覆盖表（每个源文段落有去向）、改写段落溯源表（每个改写段落有来源）。

同时 Agent 写台账文件（JSON 数组）：

- `work/evidence_map.json`：[{item_id, location(R 段号), source(源文 pid+原句), support(原文依据), rationale, verification(引擎核查结果)}]，覆盖每个数据点与关键论断；
- `work/change_log.json`：[{op(改写/压缩/删除/新增), location, before, after, reason}]（可由 change_reasons.jsonl 转写）；
- `work/uncertainty.json`、`work/manual_confirmations.json`（如文体未识别的处置假设、缺失要素待作者确认）。

## Phase 5：交付

```bash
cp /app/work/rewrite_draft.md /app/output/rewrite.md
cp /app/work/traceability_report.md /app/output/traceability_report.md
cp /app/work/change_ledger.json /app/output/change_ledger.json
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --skill "transfer-genre-ledger v1.0.4" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output --work /app/work
```

`validate_output.py` 返回非 0 时按提示修复，或将 status 降为 partial 并写明 limits。

## 异常处置表

| 异常 | 处置 |
|-|-|
| 源文缺失/为空 | 记 exceptions.json，status=failed，写明缺什么 |
| PDF 解析失败 | 试 `-layout`/OCR 工具；仍失败则降级 partial，标注无法读取部分 |
| 文体未指定/未识别 | 按科普文章模板处理，genre_recognized=false，记 manual_confirmations |
| 文体模板要素源文无法支撑 | 在成稿相应位置标注「源文未提供」，**不得编造**；记 manual_confirmations 请作者补充 |
| 源文无显式引语但通稿需要 | 引语要素标注「源文未提供」，严禁虚构研究者发言 |
| 删除含数据的源文段落 | 必须在 change_reasons.jsonl 写「删除」理由并确认是冗余；否则 ledger 判 critical |
| 新增段落含数值 | 核对来源；非源文事实必须删除或标注待确认（manual_confirmations） |
| 理由动作与对齐矛盾 | 核实是事实漂移（改稿）还是理由笔误（改 jsonl），重跑 ledger |
| 篇幅与内容冲突（必须保留项超限） | 优先保住关键结论与数据，压缩方法与背景，在 change_log 说明取舍 |
| 源文数据自相矛盾 | 不替作者裁决：两处都保留并标注，入 manual_confirmations |
| 材料不足以下笔 | 交付 partial，列缺口清单 |
| 预算过半未完成 Phase 3 | 立即跳到 Phase 5，以现有草稿交付 partial |

## 预算兜底

模型请求过半仍未完成 Phase 3：停止打磨，用当前 rewrite_draft.md 与现有 change_reasons.jsonl 直接跑 Phase 4-5，status=partial，在 uncertainty.json 写明"台账未完全闭合/未完成文体打磨"。
