---
name: longdoc-revision-ledger
description: 学位论文与长文档写作——持续修改：意见拆解与改稿落实台账（改得动）。当任务给出导师/评审修改意见（尤其是 organizer-edit-workorder.json 组织方工单，含 rounds/opinions，每条有 id/target/type/content），要求把意见拆成可执行修改项、逐条落实到章节文本、记录落实情况（before/after、证据段落、无法落实原因），或需要多轮修改合并、冲突意见裁决、修改可回退可比较（diff）时触发。不触发：从零撰写新章节（用章节规划版）、纯文献格式转换、与改稿无关的一致性核查。产出物：修订章节稿、revision_ledger（落实台账）、diff_report（行级差异）、version_report（按轮汇总+回退说明）、result.json（含 output_contract 全部字段）。
---

# 学位论文与长文档写作：意见拆解与改稿落实台账（v1.0.3）

## 0. 用途与适用条件

- 输入：`/input/case.json`、`/input/task.md`、组织方工单 `/input/organizer-edit-workorder.json`
  （兼容 rounds/opinions/items/comments/edits 等键名；每条意见含 id/target/type/content/opinion）、
  分章节工作稿、事实材料与文献库。题面声明：实际修改目标与离线本地流程范围以工单文件为准。
- 输出：`/app/output` 下的修订章节稿、`revision_ledger.md`（落实台账）、
  `diff_report.md`（作者能看懂的行级差异）、`result.json`（含 output_contract 全部字段）。
- 核心问题（题面「改得动」）：每条意见 → 可执行修改项 → 定位到段落 → 落实并记录；
  修改可回退（原件备份）、可比较（diff）、可说明（台账逐条写清改了什么、为什么改）；
  无法落实的意见如实标注原因，绝不假装完成。

## 1. 三条红线

1. **不臆造意见内容**：修改项只能来自工单 JSON 或 task.md 规则抽取的原文行；
   不得自行编造"导师意见"。before/after 摘录必须来自真实文本（chapters.json 段落原文或文件实读）。
2. **不假装落实**：无法定位、目标文件缺失、文本匹配失败、Agent 决定 skip/defer 的，
   台账如实标 `无法落实+原因` / `待人工确认`；状态判定只走 `revision_engine.py`，
   Agent 不得口头声称"已改完"。
3. **不覆盖原件先备份**：任何文本修改只在 `work/revised/` 副本上进行；
   引擎自动把原件备份到 `work/original/`，原始输入文件永不改写。

## 2. 阶段流程（Phase 0-5）

所有命令中的 `/skills/weekly-skill` 为 Skill 安装目录。工作目录 `/app/work`，产物目录 `/app/output`。

**Phase 0 — 初始化（防超时空手，必须先做）**

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md \
  --input-dir /input --work /app/work
```
Agent 动作：读 `/app/work/inspection.json`，重点确认 `workorder_files`（工单路径）、
`manuscript_candidates`（章节稿）、`output_contract`。在 `/app/work/task_notes.md` 用不超过
20 行记录：意见条数与轮次、涉及的目标文件、格式约束。

**Phase 1 — 解析章节与拆解工单**

```bash
python3 /skills/weekly-skill/scripts/parse_chapters.py <章节文件...> <材料文件...> --work /app/work
python3 /skills/weekly-skill/scripts/revision_engine.py parse \
  --workorder <inspection.json 中 workorder_files[0].path，缺省 /input/organizer-edit-workorder.json> \
  --task /input/task.md --work /app/work
```
产出 `work/workorder_items.json`：每条修改项 `{rid, round, target_file, type, content, status:pending}`。
工单缺失时自动从 task.md 抽取含 修改/补充/删除/改写/调整/统一/检查 等动词的意见行
（round=0 且标注"需人工确认"）。parse 输出 0 条 → 登记 exceptions 并转入"仅交付诊断"降级流程。

**Phase 2 — 定位与冲突裁决**

```bash
python3 /skills/weekly-skill/scripts/revision_engine.py locate --work /app/work
```
引擎按 target_file 限定 + content 关键词 2-gram 重叠取 top3 候选段落 pid，写回 `target_pids`；
两条意见定位同一 pid 且类型相反（补充 vs 删除）→ `conflicts` 标记。
Agent 动作：逐条核对 `locate_top` 摘录是否与意见语义相符——不符时在该条 items 里手工改
`target_pids`（从 chapters.json 选正确 pid，写清理由）；对每组 conflict 裁决：
保留哪条、另一条 skip/defer，理由写入 Phase 3 的 agent_edits.json。

**Phase 3 — 逐条修改决策 + 执行（apply）**

Agent 阅读每条意见的原文段落（chapters.json 中按 pid 取 `text`），写
`/app/work/agent_edits.json`：

```json
[{"rid": "R1", "action": "edit", "target_pid": "C01-S001-P003", "mode": "replace",
  "new_text": "……改写后的整段文字……", "reason": "落实意见 R1：……"},
 {"rid": "R2", "action": "skip", "reason": "无法落实的原因"},
 {"rid": "R3", "action": "defer", "reason": "需作者/导师确认的事项"}]
```

写作要求：`new_text` 必须是**完整替换段**（mode=replace，默认）或插入段
（mode=append_after 插到 target_pid 之后 / append_end 追加到文件末尾）；
保留作者原意与术语写法，只改意见要求的部分；新增数值必须可溯源到材料（溯源不了就不得新增）。
**每条 pending 意见都必须有一条决策**（edit/skip/defer 三选一），漏条会被标"待人工确认"。

```bash
python3 /skills/weekly-skill/scripts/revision_engine.py apply --work /app/work
```
产出：`work/original/`（原件备份）、`work/revised/`（修订章节）、
`work/revision_ledger.json/.md`（台账：每条意见 → 已落实/部分落实/无法落实+原因/待人工确认，
含 before/after 摘录与证据 pid）、`work/diff_report.md`（difflib 行级差异）。

**Phase 4 — 复核 + 轮次汇总（version）**

```bash
python3 /skills/weekly-skill/scripts/parse_chapters.py /app/work/revised/*.md \
  --work /app/work --out-name chapters_revised.json
python3 /skills/weekly-skill/scripts/revision_engine.py locate \
  --chapters /app/work/chapters_revised.json --items /app/work/workorder_items.json --work /app/work
```
Agent 动作：对每条"已落实"意见，确认重跑 locate 的 top1 pid 仍落在原段落且新文本包含
落实内容（抽查 after 摘录关键词）；确认 diff_report 中无意外改动（只应有台账记录的差异）；
逐条验收后执行：

```bash
python3 /skills/weekly-skill/scripts/revision_engine.py version --work /app/work
```
产出 `work/version_report.json`：按 round 汇总（每轮意见数/落实数/未落实原因）、
回退说明（work/original/ 备份路径与回退方法），并追加 change_log。

**Phase 5 — 交付**

```bash
cp /app/work/revised/*.md /app/output/   # 或按需重命名 *_revised.md
cp /app/work/revision_ledger.md /app/work/diff_report.md /app/output/
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output \
  --skill "longdoc-revision-ledger v1.0.3" --status success|partial
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```
Agent 动作：`work/evidence_map.json` 写入每条已落实意见的 {rid, claim, evidence, pid}；
`work/uncertainty.json` 写入待人工确认项；`work/exceptions.json` 汇总异常；
`work/stats.json` 记录意见数/落实数。validate 不通过 → 修复或如实降级 status=partial。

## 3. 预算兜底

模型请求超过 40 次或剩余时间不足 1/3 时：不再逐条润色 new_text，对未处理意见批量写
`{"action":"defer","reason":"预算不足，转人工处理"}`，直接跑 apply → version → Phase 5，
`status="partial"`，`stats.json` 记录 `budget_fallback=true`。骨架 result.json 已在
Phase 0 落盘，绝不空手。

## 4. 异常处置表

| 情况 | 处置 |
|-|-|
| 工单缺失（inspection.workorder_files 为空） | parse 自动回退 task.md 规则抽取（round=0，标"需人工确认"）；task.md 也无意见行 → 仅交付诊断说明，status=partial |
| 工单 JSON 格式异常/键名不识 | parse 兼容 rounds/opinions/items/comments/edits 与 id/target/type/content/opinion；仍 0 条 → exceptions 记录"工单无法解析"，降级 partial |
| 意见无法定位（locate 无候选） | 不得强行修改；agent_edits 写 skip + 原因"未定位到对应段落"，台账标 无法落实 |
| 冲突意见（同 pid 类型相反） | locate 标 conflict；Phase 2 Agent 裁决：一条 edit、另一条 skip/defer 并写明裁决理由 |
| 目标文件缺失（target_file 不在章节中） | locate 记 locate_error；apply 判定 无法落实+原因"目标文件缺失"，不创建新文件冒充 |
| 多轮意见合并冲突（后轮推翻前轮） | 按轮次顺序执行（round 升序）；后轮与已落实前轮矛盾时在台账注明"第 N 轮意见覆盖第 M 轮"，diff_report 自然呈现净效果 |
| 修改后一致性破坏（术语/编号/引用断裂） | Phase 4 复核发现即回退该条（用 work/original/ 副本还原），改 defer + 原因；不得带病交付 |
| 文本匹配失败（apply 找不到原文段） | 引擎判 部分落实/无法落实 并记原因；Agent 不得绕过引擎手改 revised 文件后声称已落实 |
| docx/pdf 章节提取降级 | parse_chapters 记 issues；能解析则正常改，不能解析的该文件意见标 无法落实 |
| 超时/预算耗尽 | 见第 3 节：批量 defer + 立即走完 apply/version/交付，骨架 result.json 保底 |

异常与不确定性一律写入 `/app/work/exceptions.json`、`uncertainty.json`
（`[{item, reason, severity}]`）。

## 5. 与其他版本的关系

本 Skill 覆盖题面「持续修改：意见拆解与改稿落实」方向。同一仓库另有章节规划与篇幅论证、
跨章节一致性、术语引用溯源、长上下文登记簿四个方向的独立 Skill（见 GITHUB_URL.txt
指向的仓库目录）。意见落实的判据细则见 references/revision_rules.md，
典型失败模式见 references/failure_modes.md。
