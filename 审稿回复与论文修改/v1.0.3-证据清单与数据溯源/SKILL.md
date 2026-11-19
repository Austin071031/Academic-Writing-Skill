---
name: revision-evidence-provenance
description: 审稿回复与论文修改的"证据补充"方向技能。当任务给出基线稿件（如 materials/manuscript-baseline.md）与审稿意见清单（如 materials/reviewer-comments.md），要求逐条处理意见、交付修订稿与逐条回复信时使用。核心能力：为需要补实验、补数据、补文献或重做分析的意见自动生成证据清单，标明到位状态（到位/部分到位/无法补做）、数据出处和无法补做时的替代说明；回复信与修订稿中的每个数字可回溯到基线段落行号或意见原文，未核实数字自动进入人工确认清单，不冒称真实补做实验或已联网核验文献。适用于受控返修演练与真实返修的证据管理阶段。
---

# 审稿回复与论文修改：证据清单与数据溯源

## 1. 用途与适用条件

本 Skill 解决返修中"证得住"环节最常见的三类失败：**答应补证据却没下文**（回复信承诺补充对比数据/文献，交付物里既无证据也无说明）、**无法补做时硬编**（编造实验数据、编造文献条目、冒称已联网核验）、**数字无出处**（修订稿和回复信里出现的数值既不在基线也不在意见原文中，来源无人能说清）。

核心原则：

1. **证据需求自动建档**：每个 needs_evidence 子要求生成一条 EV 证据条目（补实验/补数据/补文献/重做分析），同一证据被多个子要求共享时只建一条，条目内列全部 sub_id；
2. **三档到位状态**：到位 / 部分到位 / 无法补做，脚本初判、Agent 终判；无法补做必须给出替代说明（条件不存在/数据未采集/无法核验 + 等效佐证或局限声明）；
3. **数字逐条溯源**：回复信与所有已落稿修改中的每个数字（含百分数）逐一与基线全文、意见原文比对——溯源成功记到基线 P### 行号，意见给出的溯源到 comments.json 的 sub_id，邻近【待补】的记待补，其余一律未核实并自动写入人工确认；
4. **诚实红线**：不得冒称真实补做实验/已联网核验文献；基线没有的数据用【待补：…】占位并列入证据清单；可执行的文本修改不得以缺材料为由跳过。

适用条件：输入含可读的基线稿件（md/txt/tex/docx/pdf）与审稿意见文件；意见可以是编号列表、分审稿人段落或自由文本。

## 2. 输入与输出

输入：`/input/case.json`（case_id、output_contract）、`/input/task.md`、`/input/` 材料（典型为 `materials/manuscript-baseline.md` 与 `materials/reviewer-comments.md`，名称可能不同，由侦察脚本判定）。

输出（写入 `/app/output/`）：

| 文件 | 内容 |
|-|-|
| `result.json` | output_contract 全字段 + case_id + status + sources + uncertainty + change_log |
| `revised_manuscript.md` | 可编辑修订稿（锚点编辑真实应用后的全文） |
| `response_letter.md` | 逐条回复信草案（子要求级，含决策与修改指涉） |
| `edit_locations.md` | 修改定位表（操作→锚点→修订稿行号） |
| `evidence_checklist.md` | 证据清单（EV 条目：需求类型、到位状态、出处、替代说明） |
| `provenance_report.md` | 数字溯源报告（数字 \| 出现位置 \| 基线/意见来源 \| 判定） |
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

产出 `structure.json`：章节（SEC#）/段落（P###）/句子级稳定 ID。读一遍段落清单，建立稿件内容地图——后续数字溯源的 P### 与行号都来自这一步，务必确认 `source_file` 指向的基线原文可读。

### 步骤 3：解析意见并复核

```bash
python3 $SKILL/scripts/parse_comments.py --work /app/work
```

**然后由你（Agent）复核 `comments.json`**，这是证据方向的第一个关键人工判断点：

- 拆分漏了子要求 → 直接补行（保持 sub_id 递增）；拆分过碎 → 合并；
- `action_kind` 初判错误 → 修正，它直接决定证据需求类型（add_experiment→补实验 / add_data→补数据 / add_citation→补文献 / reanalysis→重做分析）；
- **`needs_evidence` 逐一确认**：凡要求补实验、补数据、补文献或重做分析的子要求必须置 true——脚本只凭关键词初判，漏标是证据清单漏项的唯一来源。

### 步骤 4：制定处置决策与编辑计划

写 `/app/work/dispositions.json`（schema 见 `references/schemas.md`）：每个子要求一条，含 `decision`、`response`（≥20 字且含可核查指涉）、`edit_ops`、`evidence`、`tone`。**需要同一证据的多个子要求在 evidence 字段引用同一个 EV 编号**（如 R1-C1 的"补对比表"与"补两篇文献"都引用 EV1），evidence_engine 据此去重建档。

写 `/app/work/edit_plan.json`：每处修改一条操作，`anchor_quote` 必须**从 structure.json 段落原文逐字复制**（≥10 字、含特征词）。无法获得真实数据的内容用 `【待补：说明】` 占位；占位写清"缺什么、向谁要"，这同时是数字溯源判定"待补"的依据。

### 步骤 4.5：证据需求建档（本方向核心一）

```bash
python3 $SKILL/scripts/evidence_engine.py --work /app/work --out /app/output --stage demand
```

生成 `work/evidence_checklist.json` 与 `/app/output/evidence_checklist.md` 草稿：每条 EV 含 demand（需求类型）、status 初判、source（基线 P### 或"材料外，待作者补充"）、note（替代说明模板）。

**然后由你（Agent）终判状态**：逐条复核——初判"到位"的是否真有证据支撑？初判"部分到位"的占位内容是否写清？确认或修改 `work/evidence_checklist.json` 的 status/source/note 后**重跑一次 demand**（脚本按 sub_ids 匹配保留你的修订），使 Markdown 草稿同步。

### 步骤 5：应用编辑

```bash
python3 $SKILL/scripts/revision_engine.py --work /app/work --out /app/output
```

exit=2 表示有失败锚点：读 `work/edit_report.json` 的 reason，修正 quote（从 structure.json 重抄）或加 `para_id`，重跑。**不得无视失败继续。** 应用完成后可再跑一次 demand，此时脚本以 edit_report 的 applied 状态为准，建档更准。

### 步骤 6：撰写回复信与配套产物

- 写 `/app/output/response_letter.md`：按审稿人→意见→子要求组织，每条含 决策 + 已做修改（引用 E# 与位置）/ 不采纳理由 / **证据状态（引用 EV# 及其到位状态）**；引用基线数据时直接写出数值（如"基线首次库仑效率 78%"），这些数字会在步骤 7 被逐条溯源；
- 写 `/app/output/edit_locations.md`（可从 `work/edit_report.json` 抄行号）；
- 复核 `/app/output/evidence_checklist.md` 草稿措辞（表格主体已由脚本生成）；
- 写 `/app/work/change_log.json`、`uncertainty.json`、`manual_confirmations.json`（初稿）、`stats.json`（格式见 references/schemas.md）。

### 步骤 7：数字溯源核验 + 交叉核验（本方向核心二）

```bash
python3 $SKILL/scripts/evidence_engine.py --work /app/work --out /app/output --stage provenance
python3 $SKILL/scripts/verify_revision.py --work /app/work --out /app/output
```

provenance 阶段自动完成三件事：回复信与全部 applied op 的 new_text 中每个数字的逐条溯源（生成 `provenance_report.md` 与 `work/provenance.json`）；为每条 EV 生成 `work/evidence_map.json`（claim/source/kind，**替代手工编写**）；把未核实数字自动并入 `work/manual_confirmations.json`。

**exit=2 是告警不是失败**：逐条处理未核实数字——确为作者掌握的数值 → 保留并确认人工确认条目已写入；来源说不清的 → 改为【待补：…】占位或删除后重跑。注意：数字来自意见原文判"意见给出"，不算未核实。verify 五重核验 FAIL 项必须修复后重跑至 PASS，无法修复的把 status 降级为 partial 并在 uncertainty 说明。

### 步骤 8：汇总交付

```bash
python3 $SKILL/scripts/assemble_result.py --work /app/work --out /app/output \
  --case /input/case.json --skill "revision-evidence-provenance v1.0.3" --status success
python3 $SKILL/scripts/validate_output.py --out /app/output --work /app/work
```

validate PASS 后结束；FAIL 按提示修复或如实降级 status。存在未核实数字或无法补做的 EV 条目时，status=success 的前提是其已全部进入 manual_confirmations 且回复信如实披露。

## 4. 异常处理

| 情况 | 处置 |
|-|-|
| 找不到意见文件或基线文件 | inspect issues 记录；status=failed 并说明缺什么，不编造内容 |
| 证据状态初判与事实不符 | 正常：状态由 Agent 终判、脚本初判仅供参考；改 work/evidence_checklist.json 后重跑 demand 保留修订 |
| 数字来自意见原文（如审稿人给的阈值） | 不算未核实：provenance 判"意见给出"并溯源到 comments.json 的 sub_id，无需人工确认 |
| 【待补】占位与"无法补做"的区别 | 占位=修改已落稿、留出填空位置（状态多为部分到位）；无法补做=连占位内容都无法确定，回复信必须给替代说明 + 人工确认 |
| 未核实数字（exit=2） | 逐条确认：作者掌握的数值→保留并确认人工确认条目；说不清来源→改【待补】或删除后重跑 provenance |
| 要求补实验/数据/文献但材料内无法完成 | 修订稿插【待补：…】占位 + 证据清单对应 EV 条目标"无法补做"+替代说明；不得编造数据或文献 |
| 多个子要求共享同一证据 | 在 dispositions 的 evidence 字段引用同一 EV 编号；脚本只建一条并列出全部 sub_id；勿重复建档 |
| 锚点多次出现（不唯一） | 加长 quote 或指定 para_id + section 后重跑 revision_engine |
| 锚点完全找不到（fuzzy<0.75） | 不得强行应用；该操作降级，disposition 改为说明"未在基线定位到对应文字"并列入 uncertainty |
| 意见本身有误（与基线事实不符） | 礼貌澄清式回复（tone=澄清），引用基线原文锚点与 P### 为据，不盲从 |
| 基线原文不可读（编码/权限） | provenance 全部数字将无法溯源；exceptions 记录并 status=partial，不得谎称已溯源 |
| 重复运行 | 脚本幂等；demand 重跑保留 Agent 修订（按 sub_ids 匹配），provenance 重跑去重合并人工确认项 |

## 5. 最小调用示例（示意，非真实案例答案）

输入（示意）：case.json 含 `{"case_id":"demo","output_contract":["revised_manuscript","response_letter","edit_locations","evidence_checklist"]}`；材料为 7 段基线 + 2 位审稿人 5 条意见，其中 R1-C1 要求"补对比表+引用近两年文献"、R1-C3 要求"补统计数据"。

调用：步骤 0→8 顺序执行；复核 comments.json 把 R1-C3-s1 的 needs_evidence 置 true；dispositions 中 R1-C1 两条子要求同引 EV1；demand 建档得 2 条 EV（EV1 共享、EV2）；revision_engine 应用 5/5；provenance 溯源 17 个数字：基线数字 12 条溯源成功（如 1450→baseline P004 L17）、3 条待补、2 条未核实进入人工确认。

示意输出（provenance 节选）：

```
[evidence_engine] demand: EV 条目=2 状态分布={'部分到位': 2}
[evidence_engine] provenance: 数字=17 溯源成功=12 意见给出=0 待补=3 未核实=2 evidence_map=3
[verify] overall=PASS  [validate] PASS (status=success, outputs=8)
```

## 6. 资源清单

- `scripts/`：init_result / inspect_case / parse_manuscript / parse_comments / revision_engine / verify_revision / assemble_result / validate_output（共享核心）+ **evidence_engine（主攻：demand 建档 + provenance 溯源）**，全部 stdlib
- `references/schemas.md`：dispositions / edit_plan / evidence_checklist / evidence_map 等全部 JSON 契约
- `references/evidence_rules.md`：四类证据需求定义、三档到位状态判据、替代说明句式、数字溯源规则
- `templates/evidence_checklist.md`：证据清单手工填写模板（脚本不可用时的兜底）
- `checklists/final_checklist.md`：交付前自查清单
- `evaluation/scoring_sheet.md`：评分点-机制对照自查表
- `examples/minimal_example.md`：最小调用示例（合成数据，标明为示例）
