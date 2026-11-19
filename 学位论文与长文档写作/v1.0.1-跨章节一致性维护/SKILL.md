---
name: longdoc-consistency
description: 学位论文与长文档写作——跨章节一致性维护（连得上）。当任务要求统一全文术语/缩写/符号写法、核对图表公式交叉引用与编号连续性、发现跨章结论相互矛盾、或评估"改动某处后哪些段落受影响"时触发；适用于多分章稿件（md/txt/tex/docx/pdf）的修订、统稿、定稿前核查。不触发：单篇短文写作、纯文献格式转换、章节规划与篇幅论证（属 v1.0.0 方向）。产出物：术语表 glossary.md、一致性报告 consistency_report、交叉引用审计 xref_audit、矛盾候选清单、影响面报告 impact_report，以及 result.json。
---

# 学位论文与长文档写作：跨章节一致性维护（v1.0.1）

## 0. 用途与适用条件

- 输入：`/input/case.json`、`/input/task.md`、分章节工作稿（`/input/**`，md/txt/tex/docx/pdf）、
  事实材料、文献库、（可选）组织方工单。
- 输出：`/app/output` 下的 `glossary.md`（术语表）、`consistency_report.md`（异写与冲突报告）、
  `impact_report.md`（改动影响面）、统稿后的章节稿（若任务要求改稿）、
  `result.json`（含 case.json `output_contract` 全部字段）。
- 核心问题（题面「连得上」）：同一概念全文写法一致；图表公式引用与定义双向对应、
  编号连续；跨章结论不自相矛盾；改动一处能列出全部受影响段落。

## 1. 三条红线

1. **不臆造术语定义**：术语候选只来自 `scan` 的模式命中与高频统计；canonical 与定义
   必须来自原文定义处（definition_pid）或 Agent 对材料的裁决，裁决理由写入
   `manual_confirmations.json`；原文没有定义的术语只登记写法、不编造定义。
2. **不臆造核验结果**：`validate_output.py` 未通过即如实降级 `status="partial"` 并在
   `issues`/result 中写明；矛盾候选只交 Agent 裁决，不得口头宣布"无矛盾"。
3. **术语统一必须走引擎复核**：Agent 执行统一修改后，必须重新 `parse_chapters` +
   `scan` + `glossary` 复跑，以 `consistency_report.json` 的异写清零（或残留均有
   `manual_confirmations` 理由）为准，不得口头声称已统一。

## 2. 阶段流程（Phase 0-5）

所有命令中的 `/skills/weekly-skill` 为 Skill 安装目录。工作目录 `/app/work`，产物目录 `/app/output`。

**Phase 0 — 初始化（防超时空手，必须先做）**

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md \
  --input-dir /input --work /app/work
```
Agent 动作：读 `/app/work/inspection.json`，确认 case_id、稿件候选、工单、约束；
通读 task.md，在 `/app/work/task_notes.md` 用不超过 20 行记录：任务类型
（术语统一/引用核查/矛盾排查/影响面评估/综合统稿）、目标范围、交付要求。

**Phase 1 — 解析材料**

```bash
python3 /skills/weekly-skill/scripts/parse_chapters.py <章节文件...> <材料文件...> --work /app/work
```
章节文件在前、事实材料在后，一次传入全部；确认段落数与交叉引用数合理；
解析 issues 非空的文件记入 `/app/work/exceptions.json`（`[{item, reason, severity}]`）。

**Phase 2 — 一致性扫描（scan）**

```bash
python3 /skills/weekly-skill/scripts/consistency_engine.py scan \
  --chapters /app/work/chapters.json --work /app/work
```
产出：
- `work/glossary_candidates.json`：术语候选三类（缩写定义型/引号书名号型/高频复合词）；
- `work/xref_audit.json`：交叉引用审计（dangling=critical、unreferenced=warn、编号连续性）；
- `work/contradiction_candidates.json`：跨章结论矛盾候选（主语重叠≥0.3 且极性相反）。

**Phase 3 — Agent 审定与裁决**

- **术语表**：逐条审定 glossary_candidates，写 `/app/work/glossary_review.json`：
  `[{"canonical": "...", "variants": [...], "definition_pid": "...", "keep": true|false}]`。
  canonical 选全文应统一的规范写法（有定义处优先用定义处写法）；variants 收全部
  认可出现的写法（缩写、英文全称、历史异写）；`keep=false` 剔除伪术语（如普通词组）。
  然后运行：
  ```bash
  python3 /skills/weekly-skill/scripts/consistency_engine.py glossary \
    --chapters /app/work/chapters.json --review /app/work/glossary_review.json --work /app/work
  ```
  产出 `work/glossary.md`、`work/consistency_report.json/.md`（逐处异写 pid+原文、
  异写率、符号/定义冲突）。
- **矛盾候选**：逐对裁决 contradiction_candidates——确属矛盾 → 按材料/文献确定
  哪方正确，列入修改计划并登记 `change_log`；实为不同条件/不同对象 → 写
  `manual_confirmations.json`（`[{item, reason, severity}]`）说明为何不算矛盾。
- **dangling 交叉引用**：逐处处理——补图表注、修正引用编号、或删除失效引用。
  **注意：xref_audit.json 的 dangling 非空时 validate_output 必 FAIL**；确实无法
  修复（如图片材料缺失）则保留记录并降级 `status="partial"`，在 result 的 issues
  与 exceptions 中写明。
- **unreferenced 与编号问题**：unreferenced 为 warn，确认是多余定义还是漏引用；
  编号不连续需统一编号后复跑 scan。

**Phase 4 — 执行统一修改 + 引擎复核**

若任务要求改稿：Agent 按 `consistency_report.md` 的逐处清单，把非规范写法改为
canonical（首次定义处保留"中文（english, ABBR）"完整形式），修复 dangling 与编号，
修改稿写回 `/app/work/revised_<原文件名>`。然后**重跑复核**：

```bash
python3 /skills/weekly-skill/scripts/parse_chapters.py /app/work/revised_*.md <材料...> \
  --work /app/work --out-name chapters_revised.json
python3 /skills/weekly-skill/scripts/consistency_engine.py scan --chapters /app/work/chapters_revised.json --work /app/work
python3 /skills/weekly-skill/scripts/consistency_engine.py glossary --chapters /app/work/chapters_revised.json \
  --review /app/work/glossary_review.json --work /app/work
```
以复跑的 `consistency_report.json` 异写数=0（或残留均有 manual_confirmations 理由）、
`xref_audit.json` dangling=0 为通过标准。

若任务要求影响面评估（"改动 X 会影响哪里"）：

```bash
python3 /skills/weekly-skill/scripts/consistency_engine.py impact \
  --chapters /app/work/chapters.json --glossary /app/work/glossary.md \
  --changed-term <术语> [--changed-sid C01-S001] --work /app/work
```
产出 `work/impact_report.json/.md`：引用该术语/xref 指向该章/结论句重叠的全部 pid。

**Phase 5 — 交付**

```bash
cp /app/work/glossary.md /app/work/consistency_report.md /app/work/impact_report.md /app/output/
cp /app/work/revised_<原文件名> /app/output/        # 若有改稿
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output \
  --skill "longdoc-consistency v1.0.1" --status success|partial
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```
Agent 动作：术语-定义映射与每处修改的出处写入 `work/evidence_map.json`；全部改动写入
`work/change_log.json`（before/after/reason）；裁决不了或材料缺失的写入
`work/uncertainty.json`。validate 不通过 → 修复或降级 status（绝不删 xref_audit.json 蒙混）。

## 3. 预算兜底

模型请求超过 40 次或剩余时间不足 1/3 时：跳过 Phase 4 的逐处改稿，直接交付
glossary.md + consistency_report + impact_report（扫描与报告类产物此时应已齐），
`status="partial"`，`stats.json` 记录 `budget_fallback=true` 与已完成阶段。
骨架 result.json 已在 Phase 0 落盘，绝不空手。

## 4. 异常处置表

| 情况 | 处置 |
|-|-|
| case.json 缺失/损坏 | init_result 记录异常；inspect 继续；case_id="unknown"，result 标注 |
| 只有单个章节文件 | 跨章检查退化为全文检查；在 stats 记录 `single_chapter=true`，矛盾候选恒为空属正常 |
| 全文无任何术语候选 | glossary_review 写空列表 `[]`；consistency_report 正常产出；在 task_notes 说明 |
| glossary_review.json 缺失/格式错 | glossary 子命令报错退出 → 修正 review 文件后重跑，不得手写 glossary.md |
| dangling 无法修复（图片/附录缺失） | 保留 xref_audit 记录，登记 exceptions，status=partial，绝不删审计文件 |
| 矛盾候选实为大字报式误报 | 逐对写 manual_confirmations 说明（不同条件/不同对象/时间演化），不强行"统一"结论 |
| 缩写一义多词（如 SSE 对应两个概念） | consistency_report 的 symbol_clash 会列出 → 更换其中一个缩写，复跑复核 |
| 同一术语两处定义不一致 | double_definition 冲突 → 以先出现定义为准或按材料裁决，裁决写入 manual_confirmations |
| docx/pdf 提取降级 | 记录 exceptions；能用则用，该文件的术语/引用结论标注置信度 |
| 编号体系混用（图3-1 vs 图3.1） | audit 统一按 `-` 归一比对；统一为任务要求的一种后复跑 |
| 改稿后复核仍有异写 | 不得口头放过：继续修或在 manual_confirmations 逐处说明保留理由（如引文原文） |

异常与不确定性一律写入 `/app/work/exceptions.json`、`uncertainty.json`。

## 5. 判据与模式表

阈值、模式、规范化规则全部见 `references/consistency_rules.md`，与
`consistency_engine.py` 顶部常量一一对应；改阈值必须两边同步。

## 6. 与其他版本的关系

本 Skill 覆盖题面「连得上」（跨章节一致性）方向。同一仓库另有章节规划与篇幅论证
（v1.0.0）、术语引用溯源、意见拆解与改稿台账、长上下文登记簿等方向的独立 Skill
（见 GITHUB_URL.txt 指向的仓库目录）。章节顺序与篇幅问题请转 v1.0.0。
