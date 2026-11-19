---
name: longdoc-citation-trace
description: 学位论文与长文档写作——术语引用统一与论断溯源（查得清）。当任务要求把论断与具体文献绑定、核验"引用了文献但结论被改写"或"引用了不存在的文献"、补齐或标记存疑引用、统一术语与缩写、或按 GB/T 7714-2015 等样式渲染参考文献表并与正文编号双向一致时触发。不触发：与引用/溯源无关的纯写作、单篇短文润色、纯文献格式转换（无溯源要求）。产出：claim_bindings.json、citation_audit.json/.md、修订稿、annotated_draft.md（⚠ 批注）、references.md（GB/T 顺序编码）、result.json。
---

# 学位论文与长文档写作：术语引用与论断溯源（v1.0.2）

## 0. 用途与适用条件

- 输入：`/input/case.json`、`/input/task.md`、分章节工作稿（`/input/**`，md/txt/tex/docx/pdf）、
  文献库（bib/ris/enw/ciw/csv/json/编号文本）、事实材料（实验记录、调研笔记等）。
- 输出：`/app/output` 下的修订稿、`citation_audit.md`、`annotated_draft.md`（存疑处 ⚠ 批注）、
  `references.md`（GB/T 7714-2015 顺序编码）、`result.json`（含 case.json `output_contract` 全部字段）。
- 核心问题（题面「查得清」）：每条含引用的论断都能落到具体文献条目；论断中的每个数值都能在
  材料中溯源；论文语气不超过材料/文献原意；不存在的引用、被改写的结论被显式标出而非静默通过；
  术语与缩写全文统一。

## 1. 三条红线

1. **不臆造文献、元数据与 DOI**：只使用 `library.json` 中真实存在的条目；解析不到的引用
   标记一律登记 unbound（critical），绝不补造条目"凑数"。
2. **不臆造核验结果**：`verify` 报出的 unverified / overstated / missing_citation 逐条如实
   呈现给作者或裁决记录；未通过复核即如实降级 `status="partial"`，不假装"全部可溯源"。
3. **引用编号必须走引擎**：编号映射、文献表渲染、连续性核对只由 `trace_engine.py` /
   `cite_engine.py` 完成，Agent 不得手改 `[n]` 编号或手写文献表条目。

## 2. 阶段流程（Phase 0-5）

所有命令中的 `/skills/weekly-skill` 为 Skill 安装目录。工作目录 `/app/work`，产物目录 `/app/output`。

**Phase 0 — 初始化（防超时空手，必须先做）**

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md \
  --input-dir /input --work /app/work
```
Agent 动作：读 `/app/work/inspection.json`，确认 `case_id`、稿件候选
（`manuscript_candidates`）、文献库候选（`library_candidates`）、材料/笔记文件与
`citation_style_hint`；把 task.md 通读一遍，在 `/app/work/task_notes.md` 用不超过 20 行记录：
任务类型（核验/修订/补引/渲染文献表）、目标样式、术语统一要求。

**Phase 1 — 解析稿件与文献库**

```bash
python3 /skills/weekly-skill/scripts/parse_chapters.py <稿件文件...> --work /app/work
python3 /skills/weekly-skill/scripts/parse_library.py <文献库文件...> --work /app/work
cat <事实材料/笔记文件...> > /app/work/materials_all.txt   # 不含稿件本身、不含文献库
```
Agent 动作：确认 `chapters.json` 段落数、`n_cite_marks` 与 `library.json` 条目数合理；
解析 issues 非空 → 记入 `/app/work/exceptions.json`（格式见 docs/USAGE.md）。

**Phase 2 — 绑定与核验（bind + verify）**

```bash
python3 /skills/weekly-skill/scripts/trace_engine.py bind \
  --chapters /app/work/chapters.json --library /app/work/library.json --work /app/work
python3 /skills/weekly-skill/scripts/trace_engine.py verify \
  --chapters /app/work/chapters.json --library /app/work/library.json \
  --materials /app/work/materials_all.txt --work /app/work
```
产出：`work/claim_bindings.json`（每条论断 → entry_ids，status ∈ bound/partially_bound/unbound）、
`work/citation_audit.json` 与 `.md`（四类问题：(a) unbound 引用存在性 critical；
(b) 数值 verbatim/derived/unverified；(c) overstated/negation_flip 语气候选；
(d) missing_citation 漏引候选及 top3 推荐条目）。
退出码 1 = 存在 unbound（critical），属预期信号，继续处理而非中止。
Agent 动作：通读 `citation_audit.md`，把四类问题逐条列入裁决清单。

**Phase 3 — Agent 裁决与修订（引擎给证据，Agent 做判断）**

对 `citation_audit.json` 逐条裁决，全部写进 `work/change_log.json`：
- **unbound（critical）**：在材料/文献库中能找到对应文献 → 修正标记或请引擎重排；
  找不到 → 删除该引用并把论断改为无来源表述或移出正文；裁决依据写入 `uncertainty.json`。
  **禁止**为凑绑定而编造文献条目。
- **unverified 数值**：材料中确无此值 → 删除/改为材料中存在的值（并在 change_log 记录
  before/after），或保留但句尾标「（数据待核）」并登记 `uncertainty.json`。禁止静默保留。
- **overstated / negation_flip 候选**：对照 `material_sentence` 原句裁决；确属升格 →
  把语气降回材料同级（如「证明」→「表明」「完全解决」→「缓解」）；误报 → 在
  `manual_confirmations.json` 写明理由。
- **missing_citation 候选**：从推荐 top3 条目中确认确为该论断来源 → 补引（编号由引擎
  在 render_refs 时确定）；推荐不准 → 在 `uncertainty.json` 登记「待作者确认来源」。
- **术语与缩写统一**：按 references/citation_rules.md 第 5 节——全文同一概念只用一种
  写法；缩写在首次出现处「全称（英文, 缩写）」定义，之后统一用缩写；把统一处理写进
  change_log。

修订稿写入 `/app/work/revised_<章节名>.md`；同时生成作者审阅版：

```bash
python3 /skills/weekly-skill/scripts/trace_engine.py annotate \
  --chapter <原稿件> --audit /app/work/citation_audit.json --work /app/work
```
产出 `work/annotated_draft.md`（正文不动，存疑处加 `> ⚠ 审校批注`）。

**Phase 4 — 复核清零与文献表渲染**

```bash
# 对修订稿重新解析 + 复核，目标：unbound=0 unverified=0 tone=0（或全部有裁决记录）
python3 /skills/weekly-skill/scripts/parse_chapters.py /app/work/revised_*.md \
  --work /app/work --out-name chapters_revised.json
python3 /skills/weekly-skill/scripts/trace_engine.py verify \
  --chapters /app/work/chapters_revised.json --library /app/work/library.json \
  --materials /app/work/materials_all.txt --work /app/work
python3 /skills/weekly-skill/scripts/trace_engine.py render_refs \
  --library /app/work/library.json --style gbt2015_numeric --work /app/work
```
`render_refs` 产出 `work/references.md`（GB/T 7714-2015 顺序编码，按正文首次出现排序）与
`work/references_audit.json`（编号连续、越界、样式一致性交叉核对）。
复核仍有 critical → 回 Phase 3 或如实降级并在 result 中说明。

**Phase 5 — 交付**

```bash
cp /app/work/revised_<章节名>.md /app/output/
cp /app/work/citation_audit.md /app/work/annotated_draft.md /app/work/references.md /app/output/
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output \
  --skill "longdoc-citation-trace v1.0.2" --status success|partial
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```
Agent 动作：把每条论断的文献绑定与数值溯源写入 `work/evidence_map.json`（格式见
docs/USAGE.md，`status=success` 时 evidence_map 不得为空）；把未决项写入
`work/uncertainty.json`；validate 不通过 → 修复或降级 status。
注意：validate 会核对 output 内全部 .md 的 `[n]` 编号 ⊆ references.md 编号；
若 annotated_draft.md 中仍保留越界标记（如 [5]），references.md 不得同时进入 output，
或状态降级为 partial 并在 uncertainty 说明（见 references/failure_modes.md）。

## 3. 预算兜底

模型请求超过 40 次或剩余时间不足 1/3 时：跳过 Phase 3 的逐条润色，只对 critical（unbound）
做最小处置（删除或标注），直接跑 Phase 4-5，`status="partial"`，`stats.json` 记录
`budget_fallback=true` 与已完成阶段。骨架 result.json 已在 Phase 0 落盘，绝不空手。

## 4. 异常处置表

| 情况 | 处置 |
|-|-|
| case.json 缺失/损坏 | init_result 记录异常；inspect 继续；case_id="unknown" 并标注 |
| 文献库缺失/解析为 0 条 | bind 全部 unbound → 如实报告；仅交付核验报告与术语表，status=partial；不编造条目 |
| 材料文件缺失（无 --materials 可用） | verify 退化为只做 (a) 引用存在性 + (c) 语气（以空材料运行），在 exceptions 记录「数值不可核」 |
| 引用样式混杂（numeric+author_year 混用） | render_refs 的 audit 报 style_consistent=false → 统一为任务要求样式（用引擎重排，不手改） |
| numeric 编号越界（如 [5] 而文献表仅 2 条） | unbound critical → Phase 3 裁决：删除/替换/请作者补文献；禁止把编号改小冒充命中 |
| author_year 作者或年份对不上 | 按 unresolved 处理；先查是否「等/et al」写法或年份后缀（2023a），仍不中则 unbound |
| 数值 masked 误判（图3-1、章节号、年份、化学式） | 引擎已遮蔽；若仍误报，在 manual_confirmations 说明该数值性质，不改引擎 |
| 语气候选误报（材料本身即为强表述） | manual_confirmations 记录「材料原文同为强语气，非升格」 |
| 漏引推荐 top3 均不相关 | uncertainty 登记「文献库无合适来源，待作者补充」；不从库外编造 |
| docx/pdf 提取降级 | 记录 exceptions；无法提取的文件不进入论断池 |
| annotated_draft 残留越界标记导致 validate FAIL | references.md 暂不出 output 或降级 partial；在 uncertainty 说明待作者裁决 |
| 预算耗尽 | 见第 3 节兜底；已落盘产物 + partial 交付 |

判据细则见 references/citation_rules.md；典型失败模式见 references/failure_modes.md。
