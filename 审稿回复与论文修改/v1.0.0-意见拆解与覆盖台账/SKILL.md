---
name: revision-comment-decomposition
description: 审稿回复与论文修改的"意见拆解"方向技能。当任务给出基线稿件（如 materials/manuscript-baseline.md）与审稿意见清单（如 materials/reviewer-comments.md），要求逐条处理意见、交付修订稿与逐条回复信时使用。核心能力：把每条意见拆成原子子要求（识别一条意见中的多个子要求），按类型/严重程度/可执行动作分类，检测跨意见重叠与冲突，建立"子要求→决策→编辑操作→证据"覆盖台账，保证答得全、不笼统致谢、不只答一半。适用于受控返修演练与真实返修的意见处理阶段。
---

# 审稿回复与论文修改：意见拆解与覆盖台账

## 1. 用途与适用条件

本 Skill 解决返修中最常见的失败：**笼统致谢**（"感谢审稿人的宝贵意见，我们已认真修改"而不逐条对应）、**只答一半**（一条意见含两个要求只回应一个）、**意见交叉无人管**（两位审稿人提了重叠或冲突的要求，回复里各说各话）。

核心原则：

1. **原子化拆解**：每条意见拆成不可再分的子要求，每个子要求有唯一 ID（如 R1-C1-s2），回复、修改、证据全部挂到子要求级。
2. **处置必有结论**：每个子要求必须落到 采纳 / 部分采纳 / 不采纳 之一，并给出理由；不允许"已认真阅读"式空转。
3. **修改必须真实落稿**：声称的每处修改通过锚点编辑引擎真实应用到基线，锚点解析失败不得谎称已改。
4. **诚实边界**：只能修订指定基线；补实验、补数据、补文献等无法在本环境完成的，以【待补：…】占位并列入证据清单，不冒称已补做。

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
| `evidence_checklist.md` | 未到位证据清单（补实验/数据/文献的需求、状态、替代说明） |
| `decomposition_report.md` | 意见拆解报告：子要求矩阵 + 重叠/冲突/依赖 + 覆盖台账审计 |
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

读 `/app/work/inspection.json`：确认 `baseline_candidates[0]` 与 `comment_candidates[0]` 是否符合预期（baseline 是稿件、comments 含 reviewer/意见标记）。若候选判定错误，后续脚本用 `--file` 显式指定。把 issues 记入 `/app/work/exceptions.json`（JSON 列表）。

### 步骤 2：解析基线结构

```bash
python3 $SKILL/scripts/parse_manuscript.py --work /app/work
```

产出 `structure.json`：章节（SEC#）/段落（P###）/句子级稳定 ID。读一遍段落清单，建立稿件内容地图。

### 步骤 3：解析并拆解意见

```bash
python3 $SKILL/scripts/parse_comments.py --work /app/work
python3 $SKILL/scripts/decompose_engine.py --work /app/work --out /app/output --stage first
```

**然后由你（Agent）复核 `comments.json`**，这是本 Skill 的核心人工判断点：

- 脚本拆分漏了子要求 → 直接在 comments.json 中补行（保持 sub_id 递增）；
- 拆分过碎（背景句被当成独立要求）→ 合并；
- type / severity / action_kind 初判错误 → 修正；
- 一条意见引用另一条（如"同意见 2"）→ 在 raw_text 保留，拆解报告第 2 节会检测重叠。

复核后重跑一次 `--stage first` 使矩阵与修订一致。

### 步骤 4：制定处置决策与编辑计划

写 `/app/work/dispositions.json`（schema 见 `references/schemas.md`）：每个子要求一条，含 `decision`（采纳/部分采纳/不采纳）、`response`（回复要点，≥20 字且含可核查指涉）、`edit_ops`、`evidence`、`tone`。

写 `/app/work/edit_plan.json`：每处修改一条操作，`anchor_quote` 必须是**从 structure.json 段落原文逐字复制的片段**（≥10 字、含特征词），动作从 replace / insert_after / insert_before / delete / replace_paragraph / append_section 选择。无法获得真实数据的内容用 `【待补：说明】` 占位。

冲突处置：若拆解报告第 3 节检出冲突，在 dispositions 中给出取舍与理由，并在回复信中说明。

### 步骤 5：应用编辑

```bash
python3 $SKILL/scripts/revision_engine.py --work /app/work --out /app/output
```

exit=2 表示有失败锚点：读 `work/edit_report.json` 的 reason，修正 quote（从 structure.json 重抄）或加 `para_id`，重跑。**不得无视失败继续。**

### 步骤 6：撰写回复信与配套产物

- 按 `templates/response_letter.md` 写 `/app/output/response_letter.md`：按审稿人→意见→子要求组织，每条含 决策 + 已做修改（引用 E# 与位置）/ 不采纳理由 / 证据状态；
- 写 `/app/output/edit_locations.md`（可从 `work/edit_report.json` 抄行号）；
- 写 `/app/output/evidence_checklist.md`：每个 needs_evidence 子要求至少一行，状态=到位/部分到位/无法补做+替代说明；
- 写 `/app/work/evidence_map.json`、`change_log.json`、`uncertainty.json`、`manual_confirmations.json`、`stats.json`（格式见 references/schemas.md）。

### 步骤 7：覆盖台账审计 + 交叉核验

```bash
python3 $SKILL/scripts/decompose_engine.py --work /app/work --out /app/output --stage audit
python3 $SKILL/scripts/verify_revision.py --work /app/work --out /app/output
```

audit 列出任何未覆盖子要求（exit=2）；verify 五重核验（覆盖/编辑声明/定位/空话/杜撰数字）。FAIL 项必须修复后重跑至 PASS，无法修复的把对应 status 降级为 partial 并在 uncertainty 说明。

### 步骤 8：汇总交付

```bash
python3 $SKILL/scripts/assemble_result.py --work /app/work --out /app/output \
  --case /input/case.json --skill "revision-comment-decomposition v1.0.0" --status success
python3 $SKILL/scripts/validate_output.py --out /app/output --work /app/work
```

validate PASS 后结束；FAIL 按提示修复或如实降级 status。

## 4. 异常处理

| 情况 | 处置 |
|-|-|
| 找不到意见文件或基线文件 | inspect issues 记录；status=failed 并说明缺什么，不编造内容 |
| 意见是无结构自由文本 | parse_comments 按段落兜底拆分；Agent 复核时手工修正 comments.json |
| 锚点多次出现（不唯一） | 加长 quote 或指定 para_id + section 后重跑 |
| 锚点完全找不到（fuzzy<0.75） | 不得强行应用；该操作降级，disposition 改为说明"未在基线定位到对应文字"并列入 uncertainty |
| 意见互相冲突 | 拆解报告第 3 节标记；dispositions 给取舍与理由；回复信说明；列入 manual_confirmations |
| 要求补实验/数据/文献 | 修订稿插【待补：…】占位 + 证据清单"无法补做+替代说明"；不得编造数据 |
| 意见本身有误（与基线事实不符） | 礼貌澄清式回复（tone=澄清），引用基线原文锚点为据，不盲从 |
| PDF 材料抽取失败 | exceptions 记录；若另一材料可读则继续并 status=partial |
| 重复运行 | 脚本幂等；重跑 revision_engine 前删除 /app/work/edit_report.json 之外无需清理 |

## 5. 最小调用示例（示意，非真实案例答案）

输入（示意）：case.json 含 `{"case_id":"demo","output_contract":["revised_manuscript","response_letter","edit_locations","evidence_checklist"]}`；材料为 8 段基线 + 2 位审稿人 5 条意见。

调用：步骤 0→8 顺序执行；parse_comments 得 5 意见 7 子要求；decompose first 产出矩阵；Agent 复核后写 5 条 edit op、7 条 disposition；revision_engine 应用 5/5；audit+verify 全 PASS。

示意输出（result.json 节选）：

```json
{
  "case_id": "demo",
  "status": "success",
  "outputs": {"revised_manuscript": "revised_manuscript.md", "response_letter": "response_letter.md",
              "decomposition_report": "decomposition_report.md", "verification": "verification.json"},
  "stats": {"n_comments": 5, "n_subs": 7, "n_ops_applied": 5},
  "verification_overall": true
}
```

## 6. 资源清单

- `scripts/`：init_result / inspect_case / parse_manuscript / parse_comments / **decompose_engine（主攻）** / revision_engine / verify_revision / assemble_result / validate_output（全部 stdlib）
- `references/schemas.md`：dispositions / edit_plan / evidence_map 等全部 JSON schema 与填写规则
- `references/decomposition_rules.md`：子要求拆分判据、类型与严重度词表、冲突/重叠裁决规则
- `references/boundary_rules.md`：诚实边界（不冒称补实验/已接收/联网核验；占位标记规范）
- `templates/response_letter.md`：回复信模板（子要求级）
- `checklists/final_checklist.md`：交付前自查清单
- `evaluation/scoring_sheet.md`：评分点-机制对照自查表
- `examples/minimal_example.md`：最小调用示例（合成数据，标明为示例）
