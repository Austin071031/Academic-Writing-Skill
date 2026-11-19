---
name: revision-point-by-point-response
description: 审稿回复与论文修改的"逐条回应"方向技能。当任务给出基线稿件（如 materials/manuscript-baseline.md）与审稿意见清单（如 materials/reviewer-comments.md），要求逐条回复并修订稿件时使用。核心能力：回复信由结构化决策台账自动生成（审稿人→意见→子要求三级，每条含决策+回应+修改指涉 E#+证据指涉 EV#），杜绝笼统致谢与虚报修改；答非所问检测按子要求动作类型核验回应是否对症；决策-语气一致性检查（不采纳必须有依据、采纳不许空转）；四档语气控制（接受/澄清/礼貌反驳/申诉）与冒犯、过度承诺、无原则顺从红线扫描。适用于受控返修演练与真实返修的回复信撰写阶段。
---

# 审稿回复与论文修改：逐条回应决策台账

## 1. 用途与适用条件

本 Skill 解决返修回复信的三类高发失败：**临场写信漏项**（Agent 凭记忆组织回复，漏意见、漏子要求）、**答非所问**（审稿人要数据，回复只致谢）、**语气失控**（冒犯审稿人、过度承诺"保证解决"、或无原则顺从"完全同意所有意见"）。

核心原则：

1. **信由台账生，不临场写**：回复信由 response_engine 依据 dispositions.json 决策台账自动装配，每个子要求一条，决策、修改指涉（E# 及 applied/failed 状态与行号）、证据指涉（EV#）全部来自结构化数据，不漏、不编。
2. **虚报必标 ⚠**：disposition 引用的修改操作若未真实应用成功，该行自动标 ⚠ 并列入信尾问题清单，禁止"声称已改但实际失败"。
3. **回应须对症**：audit 按子要求 action_kind 核验回应内容（要数据的必须引证据或写明待补，要删的必须提删，提问的必须直接回答）。
4. **语气四档可控**：每条回应在 接受/澄清/礼貌反驳/申诉 中选档，句式库见 references/response_rules.md；冒犯、过度承诺、无原则顺从三类红线逐条拦截并给改写建议。
5. **诚实边界**：基线没有的数据一律【待补：…】占位，占位不视为完成；不得冒称补做实验、已联网核验、编辑部已接收。

适用条件：输入含可读的基线稿件（md/txt/tex/docx/pdf）与审稿意见文件；意见可以是编号列表、分审稿人段落或自由文本。

## 2. 输入与输出

输入：`/input/case.json`（case_id、output_contract）、`/input/task.md`、`/input/` 材料（典型为 `materials/manuscript-baseline.md` 与 `materials/reviewer-comments.md`，名称可能不同，由侦察脚本判定）。

输出（写入 `/app/output/`）：

| 文件 | 内容 |
|-|-|
| `result.json` | output_contract 全字段 + case_id + status + sources + uncertainty + change_log |
| `revised_manuscript.md` | 可编辑修订稿（锚点编辑真实应用后的全文） |
| `response_letter.md` | 逐条回复信（台账自动生成 + Agent 润色 + audit 通过） |
| `edit_locations.md` | 修改定位表（操作→锚点→修订稿行号） |
| `evidence_checklist.md` | 未到位证据清单（需求、状态、替代说明） |
| `audit_report.json` | 答非所问 / 语气一致性 / 语气红线 / 信件完整性 审计结果 |
| `verification.json` | 五重交叉核验结果 |

## 3. 工作流程

约定：`$SKILL=/skills/weekly-skill`。全程只依赖 Python3 标准库。

### 步骤 0：立即落盘骨架（防超时空手）

```bash
python3 $SKILL/scripts/init_result.py --case /input/case.json --out /app/output
```

### 步骤 1：侦察输入

```bash
python3 $SKILL/scripts/inspect_case.py --case /input/case.json --task /input/task.md \
  --input-dir /input --work /app/work
```

读 `/app/work/inspection.json`：确认 `baseline_candidates[0]` 与 `comment_candidates[0]` 是否符合预期。若候选判定错误，后续脚本用 `--file` 显式指定。把 issues 记入 `/app/work/exceptions.json`（JSON 列表）。

### 步骤 2：解析基线结构

```bash
python3 $SKILL/scripts/parse_manuscript.py --work /app/work
```

产出 `structure.json`：章节（SEC#）/段落（P###）/句子级稳定 ID。读一遍段落清单，建立稿件内容地图。

### 步骤 3：解析意见并人工复核

```bash
python3 $SKILL/scripts/parse_comments.py --work /app/work
```

**然后由你（Agent）复核 `comments.json`**，这是核心人工判断点：拆分遗漏就补行、拆分过碎就合并、type/severity/action_kind 初判错误就修正。**action_kind 直接决定 audit 的对症判据**（add_experiment/add_data/add_citation/reanalysis/delete/format/question），务必判准——判据见 references/response_rules.md 第 4 节。

### 步骤 4：制定处置决策与编辑计划

写 `/app/work/dispositions.json`（schema 见 `references/schemas.md`）：每个子要求一条，含 `decision`（采纳/部分采纳/不采纳）、`response`（回应要点，按 action_kind 对症撰写）、`edit_ops`、`evidence`、`tone`（接受/澄清/礼貌反驳/申诉）。**response 是直接进回复信的文本**，按四档句式库写好，audit 会逐条核验。

写 `/app/work/edit_plan.json`：`anchor_quote` 必须**从 structure.json 段落原文逐字复制**（≥10 字、含特征词）；无法获得真实数据的内容用 `【待补：说明】` 占位。

若需要补实验/数据/文献，写 `/app/work/evidence_checklist.json`（EV# 条目：demand/status/source/note），供回复信引用与信尾汇总。

### 步骤 5：应用编辑

```bash
python3 $SKILL/scripts/revision_engine.py --work /app/work --out /app/output
```

exit=2 表示有失败锚点：读 `work/edit_report.json` 的 reason，修正 quote 后重跑。**不得无视失败继续**——回复信会引用每个 op 的真实状态，失败 op 会被标 ⚠ 示众。

### 步骤 6：生成回复信 → 润色 → 审计（本 Skill 主攻）

```bash
python3 $SKILL/scripts/response_engine.py --work /app/work --out /app/output --stage generate
# → 产出 /app/output/response_letter.md 草案（信首阅读说明 + 逐条回应 + 总体修改清单 + 待办与确认）
# → 你可润色措辞（不得改动决策、E#/EV# 指涉、【待补】的事实表述）
python3 $SKILL/scripts/response_engine.py --work /app/work --out /app/output --stage audit
```

- 同时写 `/app/output/edit_locations.md`（从 `work/edit_report.json` 抄行号）与 `/app/output/evidence_checklist.md`（从 `work/evidence_checklist.json` 展开）；
- audit 三类检查任一 FAIL（exit=1）必须修复：答非所问 → 按 action_kind 重写 response；语气不一致/红线 → 按四档句式库改写；修复后**重跑 generate（若改了 dispositions）+ audit 直至 PASS**；
- 写 `/app/work/evidence_map.json`、`change_log.json`、`uncertainty.json`、`manual_confirmations.json`、`stats.json`（格式见 references/schemas.md）。

### 步骤 7：交叉核验

```bash
python3 $SKILL/scripts/verify_revision.py --work /app/work --out /app/output
```

五重核验（覆盖/编辑声明/定位/空话/杜撰数字）。FAIL 项修复后重跑至 PASS；无法修复的降级 status=partial 并在 uncertainty 说明。

### 步骤 8：汇总交付

```bash
python3 $SKILL/scripts/assemble_result.py --work /app/work --out /app/output \
  --case /input/case.json --skill "revision-point-by-point-response v1.0.1" --status success
python3 $SKILL/scripts/validate_output.py --out /app/output --work /app/work
```

validate PASS 后结束；FAIL 按提示修复或如实降级 status。

## 4. 异常处理

| 情况 | 处置 |
|-|-|
| 找不到意见文件或基线文件 | inspect issues 记录；status=failed 并说明缺什么，不编造内容 |
| 意见是无结构自由文本 | parse_comments 按段落兜底拆分；Agent 复核时手工修正 comments.json |
| 意见与基线事实不符（审稿人说错了） | 决策=不采纳，tone=礼貌反驳，引基线原文锚点（P###）为据，用 response_rules.md 礼貌反驳句式；不盲从、不冒犯 |
| 同一子要求需多处修改（多 op） | edit_plan 拆成多个 op，disposition 的 edit_ops 全部列出；回复信自动逐枚引用（E1；E2…） |
| 锚点多次出现（不唯一） | 加长 quote 或指定 para_id + section 后重跑 revision_engine |
| 锚点完全找不到（fuzzy<0.75） | 不得强行应用；该操作降级，disposition 改为说明"未在基线定位到对应文字"并列入 uncertainty |
| disposition 引用了 failed/不存在的 op | generate 自动在该行标 ⚠ 并写入信尾问题清单与 work/response_problems.json；必须修复锚点或改 disposition 后重新生成 |
| 要求补实验/数据/文献 | 修订稿插【待补：…】占位 + evidence_checklist "无法补做+替代说明"；response 写明待补（audit 的 add_* 判据也要求如此）；不得编造数据 |
| 回复信被手工改过后 | **必须重跑 `--stage audit`**：红线扫描针对信件全文，润色引入的冒犯/过度承诺措辞只有 audit 能拦截 |
| audit FAIL | 按 audit_report.json 逐条修复（改 dispositions 重跑 generate，或直接改信），重跑 audit 至 PASS；禁止带 FAIL 交付 success |
| PDF 材料抽取失败 | exceptions 记录；若另一材料可读则继续并 status=partial |
| 重复运行 | 脚本幂等；generate 覆盖重写回复信草案，手工润色前请备份 |

## 5. 最小调用示例（示意，非真实案例答案）

输入（示意）：case.json 含 `{"case_id":"demo","output_contract":["revised_manuscript","response_letter","edit_locations","evidence_checklist"]}`；材料为 8 段基线 + 2 位审稿人 5 条意见。

调用：步骤 0→8 顺序执行；parse_comments 得 5 意见 7 子要求；Agent 复核后写 5 条 edit op、7 条 disposition、2 条 EV 证据；revision_engine 应用 5/5；response_engine generate 产出含 R1/R2 全部 5 意见 7 子要求的回复信；audit 四项 PASS；verify+validate PASS。

示意输出（控制台，标明为示例）：

```
[generate] 审稿人=2 意见=5 子要求=7 op=5 问题=0
[audit] off_topic/tone_consistency/tone_redlines/letter_structure: PASS
[verify] overall=PASS
[validate] PASS (status=success, outputs=7)
```

## 6. 资源清单

- `scripts/`：init_result / inspect_case / parse_manuscript / parse_comments / revision_engine / **response_engine（主攻）** / verify_revision / assemble_result / validate_output（全部 stdlib）
- `references/schemas.md`：dispositions / edit_plan / evidence_map 等全部 JSON schema 与填写规则
- `references/response_rules.md`：决策分类法定义、四档语气句式库（接受/澄清/礼貌反驳/申诉）、答非所问判据（audit 词表与此同步）
- `templates/response_letter.md`：回复信结构说明（与 generate 输出结构一致，供手工撰写/润色参照）
- `checklists/final_checklist.md`：交付前自查清单
- `evaluation/scoring_sheet.md`：评分点-机制对照自查表
- `examples/minimal_example.md`：最小调用示例（合成数据，标明为示例）
