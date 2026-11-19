---
name: longdoc-chapter-planning
description: 学位论文与长文档写作——章节规划与篇幅论证对齐。当任务要求依据大纲/提纲安排章节顺序、篇幅与论证任务，把材料组织成论文章节（而非堆砌通顺文字），或校验新写章节是否符合大纲预算、必备要素与数字可溯源性时触发。不触发：纯文献格式转换、单篇短文写作、与长文档章节结构无关的任务。
---

# 学位论文与长文档写作：章节规划与篇幅论证对齐（v1.0.0）

## 0. 用途与适用条件

- 输入：`/input/case.json`、`/input/task.md`、分章节工作稿（`/input/**`，md/txt/tex/docx/pdf）、
  大纲或提纲文件（文件名含 outline/大纲/提纲/toc 等）、事实材料与文献库。
- 输出：`/app/output` 下的章节规划、覆盖与缺口报告、按大纲撰写或校验的章节稿、
  `result.json`（含 case.json `output_contract` 全部字段）。
- 核心问题（题面「立得住」）：章节规划与提纲、论证链条、字数分配对应；
  每节明确「回答什么、需要哪些证据」；避免章节之间重复或断裂。

## 1. 三条红线

1. **不臆造事实与来源**：所有数字、术语、论断必须来自材料或文献；无法溯源的数值只登记
   `uncertainty`，不得编造出处。
2. **不臆造核验结果**：`check` 未通过即如实降级 `status="partial"` 并在 `issues` 中写明；
   不假装篇幅或要素达标。
3. **编号与篇幅只走引擎**：章节编号、预算偏差、要素完整性由 `outline_engine.py` 判定，
   Agent 不得口头声称达标。

## 2. 阶段流程（Phase 0-5）

所有命令中的 `/skills/weekly-skill` 为 Skill 安装目录。工作目录 `/app/work`，产物目录 `/app/output`。

**Phase 0 — 初始化（防超时空手，必须先做）**

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md \
  --input-dir /input --work /app/work
```
Agent 动作：读 `/app/work/inspection.json`，确认 `case_id`、大纲候选（`outline_candidates`）、
稿件候选（`manuscript_candidates`）、笔记与文献库、工单文件；把 task.md 通读一遍，
在 `/app/work/task_notes.md` 用不超过 20 行记录：任务类型（撰写新章节/修订/规划）、
目标章节、受众与格式约束。

**Phase 1 — 解析材料**

```bash
python3 /skills/weekly-skill/scripts/parse_chapters.py <章节文件...> <材料文件...> --work /app/work
python3 /skills/weekly-skill/scripts/parse_library.py <文献库文件...> --work /app/work   # 若有文献库
```
Agent 动作：从 inspection.json 取稿件与笔记文件路径（章节文件在前，事实材料在后），
`parse_chapters.py` 一次传入全部；确认输出段落数与引用标记数合理。
若某文件解析 issues 非空 → 记入 `/app/work/exceptions.json`（格式见第 4 节）。

**Phase 2 — 章节规划（plan）**

```bash
python3 /skills/weekly-skill/scripts/outline_engine.py plan \
  --chapters /app/work/chapters.json --outline <大纲文件> --work /app/work
```
产出：`work/outline.json`（条目树）、`work/chapter_plan.json`、`work/chapter_plan.md`、
`work/coverage_report.md`。
Agent 动作：阅读 coverage_report.md 中的「章节重复风险」「材料缺口」「必备论证要素完整性」；
对 `no_material_yet` 的条目，在大纲材料或笔记中补找证据，找不到则在
`work/uncertainty.json` 登记「该节无材料支撑，需人工补充」。

**Phase 3 — 按规划撰写或修订章节（Agent 写作，引擎给判据）**

撰写规则（references/planning_rules.md 有完整判据表）：
- 每节开头必须显式回答 `chapter_plan.json` 中该节的 `question`；
- 只使用 `evidence_pids` 指向的材料事实；引用已有章节术语时保持原文写法；
- 章节编号沿用全文编号体系（如已有第1、2章，新章为第3章），小节连续编号；
- 篇幅控制在预算 ±25% 内；必备要素逐条落实；
- 每个事实句在句末用 `(来源: <pid或文献>)` 内部标注（定稿前由 Agent 统一转为正文引用）。

把成稿写入 `/app/work/draft_<章节名>.md`。

**Phase 4 — 章节校验（check）**

```bash
python3 /skills/weekly-skill/scripts/outline_engine.py check \
  --chapter /app/work/draft_<章节名>.md --chapters /app/work/chapters.json \
  --plan /app/work/chapter_plan.json --materials <合并材料文本> --work /app/work
```
其中 `--materials` 指向一个合并的事实材料文本（Agent 用 `cat` 合并 facts/笔记文件到
`work/materials_all.txt`，**不得**包含大纲与章节稿本身）。
产出 `work/chapter_check.json`：`issues`（critical）、`warnings`、逐数值溯源结果。
Agent 动作：修复全部 `issues`；`warnings` 逐条判断（要素确不需要→在
`manual_confirmations.json` 说明理由；数值确无法溯源→移出正文或标注存疑）。

**Phase 5 — 交付**

```bash
cp /app/work/chapter_plan.md /app/work/coverage_report.md /app/output/
cp /app/work/draft_<章节名>.md /app/output/chapter_<N>.md
# 若任务要求文献表：
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output \
  --skill "longdoc-chapter-planning v1.0.0" --status success|partial
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```
Agent 动作：把 `chapter_check.json` 的未溯源数值写入 `work/uncertainty.json`；
把每节的证据 pid 映射写入 `work/evidence_map.json`（格式见 docs/USAGE.md）；
把章节新增/修改写入 `work/change_log.json`。validate 不通过 → 修复或降级 status。

## 3. 预算兜底

模型请求超过 40 次或剩余时间不足 1/3 时：跳过 Phase 3 的润色迭代，直接以当前
draft（哪怕未完成全部要素）跑 Phase 4-5，`status="partial"`，`stats.json` 记录
`budget_fallback=true` 与已完成阶段。骨架 result.json 已在 Phase 0 落盘，绝不空手。

## 4. 异常处置表

| 情况 | 处置 |
|-|-|
| case.json 缺失/损坏 | init_result 记录异常；inspect 继续；case_id="unknown"，result 标注 |
| 大纲文件缺失 | plan 无法执行 → 从章节稿标题重建最小大纲（chapters.json headings），在 exceptions 记录「大纲缺失，按章节标题推断」 |
| 材料为空/全部解析失败 | 仅交付章节规划框架（无证据映射），status=partial |
| 新章与已有章节编号冲突 | check 的 heading_sequence_ok=false → 修正编号后复跑，不手改其他章节 |
| docx/pdf 提取降级 | 记录 exceptions；能用则用，不能用则该文件不进入证据池 |
| 数值无法溯源 | 移出正文或改为定性表述；无法移出时句尾加「（数据来源待确认）」并登记 uncertainty |
| 章节重复风险 ≥0.5 | 与已有章节合并或改写论证角度；仍重复则在 coverage_report 标注 |
| 预算严重偏差(>50%) | 扩写/压缩后复跑 check；确实达不到则在 issues 中说明原因 |

异常与不确定性一律写入 `/app/work/exceptions.json`、`uncertainty.json`
（`[{item, reason, severity}]`）。

## 5. 与其他版本的关系

本 Skill 覆盖题面「章节规划」方向。同一仓库另有跨章节一致性、术语引用溯源、
意见拆解与改稿台账、长上下文登记簿四个方向的独立 Skill（见 GITHUB_URL.txt 指向的仓库目录）。
