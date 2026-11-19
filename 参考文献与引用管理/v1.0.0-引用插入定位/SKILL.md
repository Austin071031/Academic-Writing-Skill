---
name: citation-placement-skill
description: >-
  论断级引用插入与定位（挂得对）。当用户同时提供学术稿件与文献库（bib/ris/enw/csv/json/GB-T 文本等），
  并要求"插入引用 / 补引文 / 调整引用位置 / 整理参考文献表 / 按 GB/T 7714、APA 等格式挂引用"时触发；
  也适用于发现稿件存在"段末集中堆放引用、编号与文献表不同步、该引未引"等问题需要修复的场景。
  不触发：纯问答或闲聊；没有文献库可用的引用咨询（只给建议不做插入）；稿件格式转换、语言润色、
  文献去重合并（见v1.0.2）、编号连锁更新（见v1.0.1）、来源逐条核验（见v1.0.4）等与"插入定位"无关的任务。
  产出物：edited_manuscript.md（论断句末插好引用的全文）、references.md（按引用顺序重排的参考文献表）、
  placement_audit.json（错放审计）、result.json（含 evidence_map/change_log/exceptions）。
---

# v1.0.0｜引用插入与定位（挂得对）

核心分工：**Agent 只做判断**（哪句是论断、该不该引、引哪几条、什么形式）；
**确定性引擎做全部机械劳动**（定位句子、插入标记、全局重排编号、渲染文献表、审计错放）。
Agent 永远不亲手往稿件里写 `[n]` 数字——数字由引擎按首次出现顺序统一分配。

## 三条红线

1. **不臆造文献与元数据**：entry_ids 只能来自 `work/library.json` 里真实存在的记录；不确定的归属记 `uncertainty.json`。
2. **不臆造定位与核验**：`sentence` 在段落中定位失败时，引擎自动记 `exceptions.json` 并跳过；Agent 不得"猜一个差不多的位置"手写插入。
3. **编号只走引擎**：所有 `[n]` 的写入、合并、重排只能由 `place_citations.py` 完成；Agent 不得在任何产物里手改数字。

## 环境与路径约定

- 输入：`/input/case.json`、`/input/task.md`、材料文件（稿件 + 文献库，格式未知）。
- 工作目录 `/app/work`，最终产物 `/app/output`（必须含 `result.json`）。
- 本 Skill 安装于 `/skills/weekly-skill`，下文命令用绝对路径 `python3 /skills/weekly-skill/scripts/xxx.py`。
- 预算：64 次模型请求 / 900 秒。脚本承担机械劳动，Agent 请求主要花在 Phase 3 的逐段判断上。

## Phase 0 — 落盘骨架（防超时空手）

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
```

Agent 动作：无判断，直接执行。

## Phase 1 — 侦查输入

```bash
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 /skills/weekly-skill/scripts/parse_manuscript.py <稿件路径> --work /app/work
python3 /skills/weekly-skill/scripts/parse_library.py <文献库文件1> [文献库文件2 ...] --work /app/work
```

Agent 动作：
- 读 `work/inspection.json`：确认 case_id、稿件候选、文献库候选、`citation_style_hint` 与 task.md 中的样式要求。
- **定引用形式**：task.md 明确"顺序编码制 / GB/T 7714 numeric / Vancouver"→ `numeric`；
  明确"著者-出版年 / APA / author-year"→ `author_year`。task.md 与稿件现状不一致时**以任务书为准**，
  并在 `work/change_log.json`（由引擎合并时记录亦可由 Agent 追加）写明该决定。
- 读 `work/manuscript.json` 的段落清单（pid/kind/text/cite_marks）与 `work/library.json` 的记录（id/题名/作者/年）。

## Phase 2 — 读规则

Agent 动作：读 `/skills/weekly-skill/references/claim_rubric.md`（论断类型判定细则与正反例）与
`/skills/weekly-skill/references/placement_rules.md`（插入位置、一句多引、中英文标点规则）。
拿不准时查 `references/failure_modes.md` 对照典型错误自查。

## Phase 3 — 论断级判断（Agent 的核心工作，唯一的模型密集阶段）

逐段（只看 kind=body 的段落）识别**需要来源支撑的论断句**，写 `work/citation_decisions.jsonl`，
**每行一条 JSON**：

```json
{"claim_id": "C1", "pid": "P002", "sentence": "<从该段 text 中原样复制的论断句>", "claim_type": "quantitative_fact|others_result|method_lineage|controversial_claim|explicit_marker", "entry_ids": ["R001", "R004"], "rationale": "<一句话说明为何引、为何引这几条>", "position": "after_sentence", "form": "numeric"}
```

字段规则：
- `sentence` 必须是该 pid 段落 `text` 中**逐字存在的子串**（可不含句末标点；含换行的段落已被脚本折叠为单空格）。
- `entry_ids` 可多条 → 引擎自动合并为一个标记 `[n,m]`（一句多引）；同一文献支撑多个论断句时，在每条 decision 里各写一次（多句一引，引擎展开为同号多标记）。
- `position` 缺省 `after_sentence`（论断句末）；只有"句前引导式引用"才用 `before_sentence`。
- `form` 缺省跟随全局样式；个别句子需要不同形式时才覆盖。

**需要引用**（claim_type）：量化事实/数据；他人结论与发现；方法沿袭（"采用 X 提出的方法"）；
争议性或反直觉论断；稿件中明确标注需引用处（如"（待引）""[?]"）。
**不需要引用**：作者自己的新结果与数据；公知常识（水在 100°C 沸腾）；承上启下句、章节过渡句；
引言里的宽泛背景铺垫（无具体事实断言者）。

判断拿不准的归属（某句可能对应库里多条记录）→ 选最贴近的一条并在 rationale 写明，或记入
`work/uncertainty.json`（`[{"claim_id","issue","candidates"}]`），不要塞多条"宁可多引"。

## Phase 4 — 引擎插入与渲染（确定性，一条命令）

```bash
python3 /skills/weekly-skill/scripts/place_citations.py \
  --decisions /app/work/citation_decisions.jsonl \
  --manuscript /app/work/manuscript.json \
  --library /app/work/library.json \
  --work /app/work --out /app/output \
  --style gbt2015_numeric --form auto
```

`--style` ∈ `gbt2015_numeric | gbt2015_author | apa7 | vancouver`（按 Phase 1 的决定选择）。
引擎自动完成：句内定位（精确→空白宽容→去空白三级）→ 论断句末插入 → 同句多引合并 →
按首次出现顺序全局重排 1..N → 调用 cite_engine 渲染 `references.md`（按引用顺序）→
写 `edited_manuscript.md`（保留原段落结构与标题，旧文献表段落默认移除并记 change_log）→
写 `work/placement_audit.json`（段末 30 字符错放疑似 / 一句多引合并 / 多句一引展开）。
定位失败的 decision 进 `work/exceptions.json` 并跳过，引擎exit码仍为 0（诚实降级）。

Agent 动作：跑完后**读** `work/placement_audit.json` 与 `work/exceptions.json`：
- 有定位失败 → 检查是否自己 sentence 抄错（可从 manuscript.json 复制正确子串后重跑本阶段）；
  确认稿件确实无此句则保留 exception 并在报告中说明。
- `post_insertion_misplacement_suspects` 非空 → 视为引擎告警，核对对应 decision 的 position。

可选一致性复检（numeric 场景建议执行）：

```bash
python3 /skills/weekly-skill/scripts/cite_engine.py audit --manuscript /app/work/manuscript.placed.json --nrefs <库中条目数>
```

## Phase 5 — 汇总交付

```bash
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --case /input/case.json --skill "citation-placement-skill v1.0.0" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work --expect-status success
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output --work /app/work
```

- 有未解决 exceptions / 文献库部分解析失败 / 存在 uncertainty → `--status partial` 并去掉 `--expect-status success`。
- validate_output 必须 exit 0（打印 PASS）才可交付。

## 异常处置表

| 异常 | 处置 |
|---|---|
| case.json 缺失/损坏 | init_result 与 inspect_case 已容错；result.json case_id=unknown，继续流程，记 issues |
| task.md 缺失 | 引用形式退化为 inspection 嗅探结果；记 exceptions，status=partial |
| 稿件格式不支持（损坏 docx/pdf 无 pdftotext） | parse_manuscript 输出空段落与 issues；记 exceptions，交付 partial |
| 文献库为空/全部解析失败 | 不插入任何标记；记 exceptions，status=partial，references.md 为空表 |
| sentence 定位失败 | 引擎自动记 exceptions 并跳过（红线2，不得臆造位置） |
| entry_id 不在库中 | 引擎丢弃该条目并记 exceptions；若整句无有效条目则跳过该 decision |
| 条目缺年份（author_year） | 标记用 n.d. 占位，记 uncertainty.json |
| 编号冲突/缺口 | 引擎按首次出现重排保证 1..N 连续；placement_audit.numbering 可查 |
| 样式要求不一致（task vs 稿件） | 以 task.md 为准，记 change_log |
| 预算过半仍在 Phase 3 | 立即停笔，以已写的 decisions 跑 Phase 4-5，`--status partial` 交付 |

## 预算兜底

模型请求使用过半（>32 次）仍未完成 Phase 3：停止逐段精判，把已完成段落的 decisions 直接交 Phase 4；
未覆盖段落在 `work/uncertainty.json` 记"未及审阅的段落 pid 列表"，Phase 5 用 `--status partial`。
宁可 partial，不要空手，不要手改编号。
