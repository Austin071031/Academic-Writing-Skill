---
name: citation-renumber-chain
description: |
  参考文献编号连锁更新引擎（「编得顺」）。什么时候触发：任务书要求对已有顺序编码制
  （numeric / GB/T 7714 顺序编码）稿件做引用条目层面的编辑——删除某几篇文献、调整文末
  列表顺序、把文献库中已有条目插入列表、两章合并后引用条目去重（merge）、增删段落导致
  引用集合变化，并要求正文引用编号、文末列表、图注/表注/附录/脚注中的引用全部同步、
  编号连续无缺口时。什么时候不触发：从零撰写新引文（用v1.0.0证据驱动流程）；文献去重
  本身不是目标（v1.0.2）；纯格式转换/样式迁移（用 cite_engine convert）；著者-出版年稿件
  只做排序检查与 stale 标注，不做数字重排。产出物：/app/output/edited_manuscript.md
  （连锁重排后的全文）、references.md + references.json（重建的文末列表，含每条出处
  source_file+source_index）、renumber_report.md（操作清单→映射表→悬空清单→终检结论）、
  preview.html。
---

# v1.0.1｜编号连锁更新（编得顺）

**核心创新（对齐评分"创新增益"）**：全确定性编号连锁更新引擎。Agent 只从任务书识别
编辑操作并写成 `work/edit_ops.json`（语义化操作列表）；一切编号重排、正文标记/文末列表/
图表注/附录/脚注引用同步，全部由 `scripts/renumber_plan.py` 编译 mapping 并驱动共享
`cite_engine renumber` 完成。引擎保证不变量：正文最大编号 == 列表条数；1..N 无缺口；
无悬空引用；无样式混杂。这是"机械化零幻觉"方向——**Agent 禁止手工改正文里的任何数字**。

## 三条红线

1. **不臆造文献/元数据**：列表条目只能来自输入文献库或稿件自带列表；插入新条目必须
   用 `insert_existing` 引用 library.json 中真实存在的记录号（R00X）。
2. **不臆造核验结果**：终检 PASS/FAIL 以引擎 stdout 的 `INVARIANTS: PASS/FAIL` 与
   `work/renumber_report.json` 的 `PASS` 字段为准，不得口头声称通过。
3. **改编号必须走引擎**：任何编号变动必须经 `edit_ops.json → renumber_plan.py`；
   禁止 Agent 直接编辑正文/图注/列表里的 `[n]` 数字。Agent 对正文唯一允许的改动是
   **改写句子语义**（删引、改引、补引），改完重跑引擎，由引擎统一重排。

## Phase 0 — 初始化与体检（防超时空手）

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
```

Agent 做什么：读 `/app/work/inspection.json`，确认 case_id、稿件候选、文献库候选、
`citation_style_hint`（numeric 还是 author_year）与 output_contract。若 style 为
author_year，跳到 Phase 3 的分支说明。

## Phase 1 — 解析材料

```bash
python3 /skills/weekly-skill/scripts/parse_manuscript.py <稿件路径> --work /app/work
python3 /skills/weekly-skill/scripts/parse_library.py <文献库文件...> --work /app/work
```

Agent 做什么：读 `work/manuscript.json` 的 `styles_detected` 与段落 kind 分布；确认
`work/library.json` 记录数 N 与 id（R001…RNNN）。**判据**：`styles_detected` 含
`numeric` 才走数字连锁更新；只有 `author_year` 走 Phase 3 著者-出版年分支。
若稿件自带文末列表但 parse 未覆盖（如列表无 `[n]` 前缀、编号格式特殊），Agent 手工把
列表条目写成 `work/reference_list.json`：`[{"num": 1, "text": "..."}, ...]`，引擎将以
它作为当前列表基准（允许文献库记录数 > 列表条数）。

## Phase 2 — 识别编辑操作（Agent 的核心判断，唯一允许"动脑子改文件"之前的阶段）

通读 `/input/task.md` 与稿件全文，把任务书要求翻译成 `work/edit_ops.json`。
操作 schema 与 20 个例子见 `references/edit_ops_schema.md`。识别细则：

| 任务书信号 | 操作 | edit_ops 写法 |
|---|---|---|
| "删除文献/不引用某篇/该文已撤稿" | `delete` | `{"op":"delete","ref_id":"R007","note":"..."}`；ref_id 也接受纯数字（=当前列表序号） |
| "把 X 调到最前/第 k 位" | `reorder` | `{"op":"reorder","ref_id":"R003","to":1}` |
| "按 …… 顺序排列这几篇" | `reorder`（子集全序） | `{"op":"reorder","ref_ids":["R002","R005","R001"],"note":"给出子集的目标相对顺序，其余保持"}` |
| "补充引用库中已有的某篇/加入新文献" | `insert_existing` | `{"op":"insert_existing","ref_id":"R012","to":3}`；只能引用 library.json 中真实存在的 R00X |
| "两章合并/重复文献合并/去重保留某条" | `merge` | `{"op":"merge","ref_ids":["R003","R008"],"keep":"R003","note":"..."}`；keep 以外的条目从列表删除 |
| "删除某段/某节" | 先 `delete` 该段引用的独有条目 | 段落本身的增删由 Agent 在 `work/manuscript.json` 上完成（改 text/cite_marks），编号仍交给引擎 |

识别原则：**只写任务书明确要求的操作**，每条带 `note` 注明出处句；不确定的操作宁可
不写（跑空操作=恒等映射，无害），也不要猜。写完后自查：每个 ref_id 能在 library.json
或当前列表中找到；位置语义——R00X 按条目身份定位（删改后仍在原位含义），纯数字按
"当前第 k 位"定位。

```bash
python3 - <<'EOF'
import json
ops = json.load(open('/app/work/edit_ops.json'))
assert isinstance(ops, list)
print(f"[check] {len(ops)} 个操作:", [o.get('op') for o in ops])
EOF
```

## Phase 3 — 引擎连锁更新（Agent 不动编号）

```bash
python3 /skills/weekly-skill/scripts/renumber_plan.py --work /app/work --out /app/output \
  --engine /skills/weekly-skill/scripts/cite_engine.py
```

引擎自动完成：编译 旧号→新号 mapping（删除=null）→ 调 `cite_engine renumber` 重排
**全部**段落（body/heading/figure_note/table_note/appendix/footnote/reference_list，
含 `[n-m]` 区间自动压缩、一句多引 `[1,3,5]`）→ 重建文末列表（删条目、按新序输出、
每条保留 `source_file+source_index` 出处）→ 写 `renumber_report.md`（人读）与
`work/renumber_report.json`（机读）→ 不变量终检，stdout 末行输出
`INVARIANTS: PASS` 或 `INVARIANTS: FAIL`。

Agent 做什么：读 `/app/output/renumber_report.md` 的"悬空引用清单"。
- **有悬空**：对被删后仍被引用的段落，Agent 改写句子（删除该引、或改引存活条目、或
  补写新引如 `[R012 的库编号]`），直接改 `work/manuscript.json` 对应段落 text 与
  cite_marks，然后**重跑本 Phase 命令**直至 PASS。禁止顺手改数字。
- **无悬空且 PASS**：进入 Phase 4。

**著者-出版年分支**：引擎不做数字重排，自动转为检查列表排序（按第一作者）并标注
stale 条目（缺 year/authors 的条目，排序键不可靠），报告说明。Agent 只需按报告
建议人工确认列表排序，把 stale 条目写入 `work/uncertainty.json`。

## Phase 4 — 审计与记录

```bash
python3 /skills/weekly-skill/scripts/cite_engine.py audit --manuscript /app/work/manuscript.renumbered.json --nrefs <列表条数>
```

Agent 做什么：`<列表条数>` 取 `work/renumber_report.json` 的
`invariants.list_entries`。读 `work/consistency_audit.json`，确认无越界/缺口/样式混杂
（应与引擎终检一致；不一致以引擎为准并记入 exceptions）。
同时把以下内容落盘（供 assemble 汇总）：
- `work/evidence_map.json`：每条 edit op 的任务书出处（[ {entry_id/claim_id, location:
  "task.md 第几句 / 段落 pid", source, support, rationale} ]）；
- `work/change_log.json`：[{op, location, before: 旧号, after: 新号/删除, reason}]，
  可从 `work/renumber_report.json` 的 mapping 直接生成；
- `work/uncertainty.json`、`work/exceptions.json`、`work/stats.json`（按需）。

## Phase 5 — 汇总交付

```bash
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output \
  --skill "citation-renumber-chain v2.0.0" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --expect-status success
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```

`--status` 判据：引擎终检 PASS 且无未处置悬空 → `success`；否则一律 `partial` 并在
`work/exceptions.json` 写明 limits（如"N 处悬空待处置，正文句子需人工改写"）。
validate 必须 exit 0 才算交付完成；exit 1 时按提示修复或降级 status 后重跑。

## 异常处置表

| 异常 | 处置 |
|---|---|
| edit_ops 里 ref_id 定位失败 | 引擎跳过该操作并记入 `ops_errors`，报告可见；Agent 核对 ref_id 写法后修正重跑 |
| 删除的条目仍被正文引用 | 引擎列悬空清单 + FAIL；Agent 改写句子或改引后重跑（流程内正常状态，非异常） |
| 字段缺失/DOI 解析失败 | 不阻断编号更新；对应条目在列表文本中如实缺字段，记入 uncertainty.json |
| 条目歧义（任务书指代不清，如"删掉那篇电池综述"对应多条） | 不按猜的执行；写入 manual_confirmations.json，edit_ops 中不删任何一条，交付 partial |
| 编号冲突（正文出现大于列表数的编号） | audit 报 out_of_range；Agent 在 exceptions.json 记录，正文该处多半是笔误，需任务书确认后处置 |
| 不支持的稿件格式（pdf 无 pdftotext / docx 损坏） | parse_manuscript 降级输出空段落+issues；Agent 如实记录，status=partial |
| 文献库为空 | 引擎无法建立列表基准 → INVARIANTS: FAIL；Agent 在 exceptions.json 说明"无文献库，仅交付原稿"，status=partial |
| 超预算（模型请求过半仍未完成 Phase 3） | 立即以**当前已有** edit_ops（哪怕不完整）跑 Phase 3-5，status=partial，limits 写明未识别的编辑操作；不得为空 edit_ops 而停摆——空操作也会产出恒等映射报告 |

## 预算兜底

若模型请求过半仍未完成 Phase 3：跳过剩余判断，用已写出的 edit_ops.json（可为空列表，
引擎按恒等映射交付）直接跑 Phase 3→4→5，`--status partial`，在
`work/exceptions.json` 写明"edit_ops 可能不完整，以下为已识别部分"。**任何情况下
Phase 0 的 init_result.py 必须先跑，Phase 5 的收尾三件套必须最后跑。**
