---
name: transfer-terminology-lock
description: 科研成果转化写作——术语锁定与跨文体一致方向。当任务要求把论文、技术报告等科研材料改写为科普文章、新闻通稿、简报或项目申报材料，且需要保证同一技术概念在全文及多种产出中说法统一（缩写首次展开、同义词/异写收敛、符号写法唯一、跨文体术语替换）时触发；为纯语言润色、从头撰写论文、引用管理或无需术语一致性的单句翻译时不触发（有专门 Skill）。产出：锁定术语表（机读 JSON + 人读 md）、达标改写稿（.md）、术语一致性审计报告（逐条定位）、逐条来源映射与修改记录。
---

# 科研成果转化写作：术语锁定与跨文体一致

把科研材料改写为目标文体稿件时，先建立**可锁定术语表**，再以引擎强制"同一概念、全文同说法、跨产物同口径"：缩写首次展开、中文异写收敛、化学式/符号写法唯一、跨文体替换有依据。脚本承担全部机械核查（异写检测、展开核查、跨文件比对），Agent 只做审定与写作。

## 三条红线

1. **不臆造术语全称**：源文未给出处的缩写/符号全称，标注待确认并用描述性说法替换，不得猜测拼出全称。
2. **不臆造核验结果**：`terminology_engine.py audit` 未通过（exit≠0）时不得声称术语已统一，必须修复或如实降级为 partial。
3. **术语统一必须走术语表**：所有说法变更只能先改 `term_table.json` 再重跑 audit；不得绕开术语表在稿中逐处手改口径。

## 运行环境约定

- 输入：`/input/case.json`、`/input/task.md`、材料文件（md/txt/tex/pdf/docx）。
- 中间产物：`/app/work`；最终交付：`/app/output`（含 result.json）。
- 本 Skill 安装于 `/skills/weekly-skill`，命令均用绝对路径；也可用 `$SKILL_DIR` 替换。
- 预算：64 次模型请求 / 900 秒。脚本秒级完成；把请求留给审定与改写。

## Phase 0：落盘骨架（防超时空手）

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
```

## Phase 1：解析任务与材料

```bash
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
```

Agent 读 `/app/work/inspection.json`：确认 `audience`、`genre`（可能含多种产物文体）、`length_limit`、`source_candidates`。若材料含 PDF，先用 `pdftotext <pdf> /app/work/source.txt` 转文本；失败试 `-layout`，再失败记 exceptions.json 并转 Phase 5 降级交付。**若 task.md 要求多份产物（如科普文章＋简报），逐份记录文体要求，audit 阶段用 `--more` 一并审计。**

## Phase 2：源文结构化与机选术语表草稿

```bash
python3 /skills/weekly-skill/scripts/parse_source.py <源文文件...> --work /app/work
python3 /skills/weekly-skill/scripts/terminology_engine.py candidates --source /app/work/source.json --work /app/work
```

Agent 读 `work/term_table_draft.json`（schema 见 references/terminology_rules.md）：每条含
`term_id / canonical / variants / kind(zh_term|acronym|symbol) / first_expand / cross_genre / note`。
机选已合并：全称↔缩写配对（"全称（ABBR）"与"ABBR（全称）"）、相似度≥0.70 的中文异写
（如"固态电解质/固体电解质"）、大小写/连字符/空格变体（如"Li-ion/Li ion"）。

**Agent 审定并另存为 `work/term_table.json`**（audit 只认审定后的表）：

- 逐条确认 canonical 是否是该概念的"标准说法"（通常取源文全称/最高频写法）；
- variants 补漏删错：机选噪声条目删除，源文出现但漏检的异写手工补入；
- first_expand：面向公众/学生/跨学科受众的缩写应为 true；本领域同行可 false；
- cross_genre：按 task.md 要求的文体逐栏确认替换建议（项目申报材料通常"保留"）；
- 源文未给全称的缩写：canonical 保持缩写，note 写明"全称待确认"，并把确认项写入
  `work/manual_confirmations.json`；**不得猜测全称**。

## Phase 3：撰写改写稿（严格按锁定术语表）

Agent 依据 term_table.json 把源文改写为完整、可直接使用的目标文体稿件，写入
`/app/work/rewrite_draft.md`（多产物任务再写 `work/briefing.md` 等）。写作要求：

- 完整成稿（标题+正文），不是提纲、建议或片段；
- **每个术语只用 canonical**；缩写首次出现写"全称（缩写）"，之后可用缩写；
  跨文体替换按该产物文体对应的 cross_genre 栏执行；
- 源文的关键结论、数据、单位、样本量、图表引用、限定条件必须保留；
- 论断强度与源文一致（初步结果不得写成定论）；
- 发现表外新说法：先改 term_table.json（补 variants 或新增条目），再写入稿件。

## Phase 4：对齐与术语一致性审计

```bash
python3 /skills/weekly-skill/scripts/align_rewrite.py --source /app/work/source.json --rewrite /app/work/rewrite_draft.md --work /app/work
python3 /skills/weekly-skill/scripts/terminology_engine.py audit --table /app/work/term_table.json --rewrite /app/work/rewrite_draft.md --more /app/work/briefing.md --work /app/work
```

（无第二份产物时省略 `--more`。）Agent 读 `terminology_audit.json/.md` 与 `alignment.json`：

- `critical`（acronym_not_expanded 缩写未展开 / symbol_conflict 一缩写两展开）**必须修复后重跑 audit，直至 exit=0**；
- `warn`（variant_used 异写 / cross_file_inconsistent 跨产物不一致 / unlocked_change 未登记新说法）逐条统一；确属"新概念/可接受说法"的，先修订 term_table.json 再重跑；
- `alignment.dropped`：源文段落未覆盖——有意删的在 change_log 写明理由，非故意的补回；
- `alignment.added`：改写新增段落——确认不含源文外事实，否则删除或标注待确认。

同时 Agent 写台账文件（JSON 数组）：

- `work/evidence_map.json`：[{item_id, location(R 段号), source(源文 pid+原句), support, rationale, verification}]，覆盖每个数据点、关键论断与**每条术语的 canonical 依据**；
- `work/change_log.json`：[{op(改写/压缩/删除/新增/术语统一), location, before, after, reason}]，术语统一类改动逐条登记（before=异写，after=canonical）；
- `work/uncertainty.json`、`work/manual_confirmations.json`（全称待确认、术语歧义处置假设等）。

## Phase 5：交付

Agent 把 term_table.json 转写为人读术语表 `work/term_table.md`（每条目一行：canonical、
variants、kind、first_expand、cross_genre 三栏、note），然后：

```bash
cp /app/work/rewrite_draft.md /app/output/rewrite.md
cp /app/work/term_table.md /app/output/term_table.md
cp /app/work/terminology_audit.md /app/output/terminology_audit.md
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --skill "transfer-terminology-lock v1.0.3" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output --work /app/work
```

`validate_output.py` 返回非 0 时按提示修复，或将 status 降为 partial 并写明 limits。

## 异常处置表

| 异常 | 处置 |
|-|-|
| 源文缺失/为空 | 记 exceptions.json，status=failed，写明缺什么 |
| PDF 解析失败 | 试 `-layout`/OCR 工具；仍失败降级 partial，标注无法读取部分 |
| 受众未指定 | 按"公众/科普读者"处理（缩写 first_expand=true），记 manual_confirmations |
| 文体未指定 | cross_genre 按科普文章栏执行，记 manual_confirmations |
| 篇幅与内容冲突 | 优先保住关键结论/数据与术语展开首次出现处，压缩背景，change_log 说明取舍 |
| 缩写无全称 | 不猜测：canonical 保留缩写，稿件用描述性说法，全称入 manual_confirmations |
| **术语歧义**（两种写法无法判定是否同一概念，如"固态电解质/固体电解质"可能特指也可能泛指） | **保留源文原说法不强行收敛**，在 term_table 分立条目并注明歧义，入 manual_confirmations 请作者确认 |
| 源文数据自相矛盾 | 不替作者裁决：两处保留并标注，入 manual_confirmations |
| 同一缩写源文本身两种展开 | 以首次出现处展开为 canonical，另一展开入 variants 并标注"源文不一致"，入 manual_confirmations |
| 材料不足以下笔 | 交付 partial，列缺口清单 |
| audit warn 无法清零（如受众需要保留两种说法） | 在 term_table note 写明保留理由，重跑确认无 critical 后在 uncertainty.json 声明 |
| 预算过半未完成 Phase 3 | 立即跳到 Phase 5，以现有草稿+术语表交付 partial |

## 预算兜底

模型请求过半仍未完成 Phase 3：停止打磨，用当前 term_table.json 与 rewrite_draft.md
直接跑 Phase 4-5，status=partial，在 uncertainty.json 写明"未完成术语审计打磨/审定不充分"。
