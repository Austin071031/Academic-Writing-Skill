---
name: transfer-audience-adapt
description: 科研成果转化写作——受众适配与可读性方向。当任务要求把论文、技术报告等科研材料改写为面向指定读者（公众、学生、投资人、政策制定者、跨学科同行等）的科普文章、新闻稿、简报或申报材料时触发；为事实保留核验、引用管理、纯语言润色或从头撰写论文时不触发（有专门 Skill）。产出：受众画像与术语处置计划、达标改写稿（.md）、可读性核查报告、逐条来源映射与修改记录。
---

# 科研成果转化写作：受众适配与可读性

把科研材料改写为目标读者"不补背景就能读懂"的稿子，同时保证事实不漂移。脚本承担全部机械核查（句长、缩写展开、术语解释、篇幅），Agent 只做判断与写作。

## 三条红线

1. 不臆造源文外的事实、数据、文献与全称；源文未给出处的缩写全称标注待确认，不得猜测。
2. 不臆造核验结果：`audience_engine.py check` 未通过（exit≠0）时不得声称达标，必须修改或如实降级。
3. 数字、单位、图表编号必须与源文逐值一致；任何换算只能走引擎/算式验证，不得凭印象改写。

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

Agent 读 `/app/work/inspection.json`：确认 `audience`（受众）、`genre`（文体）、`length_limit`（篇幅）、`source_candidates`（源文）。若材料含 PDF，先用 `pdftotext <pdf> /app/work/source.txt` 转文本；失败则尝试 `pdftotext -layout`，再失败记入 exceptions.json 并转 Phase 5 降级交付。

## Phase 2：源文结构化与受众画像

```bash
python3 /skills/weekly-skill/scripts/parse_source.py <源文文件...> --work /app/work
python3 /skills/weekly-skill/scripts/audience_engine.py profile --inspection /app/work/inspection.json --source /app/work/source.json --work /app/work
```

Agent 读 `audience_profile.json`：

- `jargon_plan`：每个缩写/术语的处置动作（首次展开后使用 / 展开或替换 / 解释后使用 / 保留）与提示语。**改写时必须逐条执行**；对"源文未给全称"的缩写，用中文描述性说法替换（如"一种表面分析技术"），并把全称确认写入 manual_confirmations。
- `writing_targets`：句长上限、平均句长目标、术语密度上限、篇幅上限。

## Phase 3：撰写改写稿

Agent 依据受众画像与术语计划，把源文改写为完整、可直接使用的目标文体稿件，写入 `/app/work/rewrite_draft.md`。写作要求：

- 完整成稿（标题+正文），不是提纲、不是建议、不是片段；
- 源文的关键结论、数据、单位、样本量、图表引用、限定条件必须保留；删掉的是冗余不是证据；
- 论断强度与源文一致（初步结果不得写成定论，相关不得写成因果）；
- 面向目标受众控制句长与术语密度，术语首次出现给解释或类比。

## Phase 4：对齐与可读性核查

```bash
python3 /skills/weekly-skill/scripts/align_rewrite.py --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --work /app/work
python3 /skills/weekly-skill/scripts/audience_engine.py check --rewrite /app/work/rewrite_draft.md --work /app/work
```

Agent 读 `readability_report.json` 与 `alignment.json`：

- `critical` 问题（缩写未展开、篇幅超限）**必须修复后重跑 check**，直至 exit=0；
- `warn` 问题（超长句、未解释术语、术语密度）逐条修改或写明保留理由；
- `alignment.dropped`：源文段落未被覆盖——判断是否"有意删除的冗余"，有意删除的在 change_log 写明理由，非故意的补回；
- `alignment.added`：改写新增段落——确认只是过渡句/背景重述，若含任何源文外事实必须删除或标注待确认。

同时 Agent 写三个台账文件（JSON 数组）：

- `work/evidence_map.json`：[{item_id, location(R 段号), source(源文 pid+原句), support(原文依据), rationale, verification(引擎核查结果)}]，覆盖每个数据点与关键论断；
- `work/change_log.json`：[{op(改写/压缩/删除/新增), location, before, after, reason}]；
- `work/uncertainty.json`、`work/manual_confirmations.json`（如全称待确认、受众未明示的处置假设）。

## Phase 5：交付

```bash
cp /app/work/rewrite_draft.md /app/output/rewrite.md
cp /app/work/readability_report.md /app/output/readability_report.md
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --skill "transfer-audience-adapt v1.0.0" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output --work /app/work
```

`validate_output.py` 返回非 0 时按提示修复，或将 status 降为 partial 并写明 limits。

## 异常处置表

| 异常 | 处置 |
|-|-|
| 源文缺失/为空 | 记 exceptions.json，status=failed，写明缺什么 |
| PDF 解析失败 | 试 `-layout`/OCR 工具；仍失败则降级 partial，标注无法读取部分 |
| 受众未指定 | 按"公众/科普读者"处理，记 manual_confirmations |
| 文体未指定 | 按科普文章模板处理，记 manual_confirmations |
| 篇幅与内容冲突（必须保留项超限） | 优先保住关键结论与数据，压缩方法与背景，在 change_log 说明取舍 |
| 缩写无全称 | 中文描述性说法替换，全称确认入 manual_confirmations |
| 源文数据自相矛盾 | 不替作者裁决：两处都保留并标注，入 manual_confirmations |
| 材料不足以下笔 | 交付 partial，列缺口清单 |
| 预算过半未完成 Phase 3 | 立即跳到 Phase 5，以现有草稿交付 partial |

## 预算兜底

模型请求过半仍未完成 Phase 3：停止打磨，用当前 rewrite_draft.md 直接跑 Phase 4-5，
status=partial，在 uncertainty.json 写明"未完成可读性打磨"。
