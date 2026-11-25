---
name: intro-background-grounding
description: >-
  研究背景立得住：引言背景的事实锚定与空转铺垫审计。当用户提供论文底稿（含方法/结果）与文献库/阅读笔记，
  要求"写引言 / 起草研究背景 / 修改引言背景 / 写引言与相关工作"时触发；亦适用于发现背景段落存在
  "近年来受到广泛关注""随着……的快速发展"等空转铺垫、背景论断无出处、背景与研究问题脱节等问题的修复场景。
  不触发：纯文献格式转换、参考文献编号维护、全文语言润色、与引言写作无关的结构诊断或结果复现任务。
  产出物：introduction.md（证据锚定的引言成稿）、related_work.md（相关工作成稿）、references.md
  （GB/T 7714 顺序编码文献表）、anti_fluff_audit.md（空转铺垫审计）、evidence_map.json（逐条来源映射）、
  build_report.json 与 result.json（含异常与不确定性记录）。
---

# v2.0.1｜文献库缺失兜底（父 v1.0.0 + salvage_library 抢救）

核心分工：**Agent 只做判断与写作**（选事实、写句子、定论断归属）；**确定性引擎做全部机械劳动与核验**
（材料解析、事实候选抽取、锚点解析、引用编号注入、文献表渲染、空转句式审计）。
背景段落的每一句具体事实论断都必须挂 〔E#〕 证据锚点；无法落到材料的一律标 type=judgment 或删去。

## 三条红线

1. **不臆造事实与数字**：正文中的每个数字、结论、转述必须能在 evidence_map.json 的某条 quote 中找到；
   引擎做数字泄漏检查，泄漏即告警。
2. **不手写引用编号**：正文只写 〔E#〕 锚点；`[n]` 引用编号一律由 build_deliverables.py 按首次出现顺序注入。
   在工作稿中手写 `[3]` 之类编号会被检出并告警。
3. **空白与贡献必须可回溯**：研究空白由 gap 推导链登记；贡献由稿件证据位置支撑；做不到就标 uncertainty 或
   judgment，不得硬写。

## 环境与路径约定

- 输入：`/input/case.json`、`/input/task.md`、材料文件（稿件 / 文献库 bib,ris,enw,csv,json,GB-T 文本 / 阅读笔记 md,txt,json）。
- 工作目录 `/app/work`，最终产物 `/app/output`（必须含 `result.json`）。
- 本 Skill 安装于 `/skills/weekly-skill`，命令一律用绝对路径 `python3 /skills/weekly-skill/scripts/xxx.py`。
- 预算：64 次模型请求 / 900 秒 / 每次响应 ≤16384 token。Phase 3 是唯一模型密集阶段，控制在 20 次请求内。

## Phase 0 — 落盘骨架（防超时空手，无判断）

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
```

## Phase 1 — 侦查与解析

```bash
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
```

Agent 动作：读 `/app/work/inspection.json`，确认 case_id、manuscript_candidates、library_candidates、
notes_candidates、language_hint、citation_style_hint、output_contract。

```bash
python3 /skills/weekly-skill/scripts/parse_manuscript.py <稿件路径> --work /app/work
python3 /skills/weekly-skill/scripts/parse_library.py <文献库文件...> --work /app/work
python3 /skills/weekly-skill/scripts/parse_notes.py <笔记文件...> --work /app/work
python3 /skills/weekly-skill/scripts/salvage_library.py --work /app/work
python3 /skills/weekly-skill/scripts/extract_facts.py --work /app/work
```

- 稿件取 inspection 中 manuscript_candidates 里尺寸最大者；无稿件候选时把 other_files 中的正文类文件
  当稿件解析，并在 exceptions 记录。
- **v2.0.1 文献兜底（本版单点改动）**：salvage_library.py 在 library.json 为空时自动从稿件参考文献段
  （reference_list 段落）与笔记编号条目抢救文献记录（GB/T 7714/编号英文/APA 近似形态），并给每条
  标注 salvage_confidence（high/medium/low）。已有文献库时该脚本为 no-op。
  Agent 动作：运行后检查 work/library.json——若 salvage 成功，低置信条目（low/medium）在
  uncertainty.json 登记"文献元数据由参考文献段抢救，建议作者核对"；引用这类条目照常，
  元数据以抢救字段为准，不得自行补全缺失字段（如 DOI）。
- 笔记文件可为空列表（parse_notes 允许零文件）。
- 读 `work/fact_candidates.jsonl`：这是可引用事实候选清单（含 manuscript 自身结果、笔记摘录、文献元数据），
  每条带 fid 与 loc 锚点。

## Phase 2 — 读本版本方法规则

依次读（都在 /skills/weekly-skill/references/ 下）：

1. `background_method.md` —— 背景三段式（脉络→矛盾→具体问题）与锚定规则；
2. `anti_fluff_patterns.txt` —— 空转铺垫句式清单（引擎审计用同一清单）；
3. `evidence_anchor_rules.md` —— evidence_map 与 claim_bindings 的字段细则；
4. `failure_modes.md` —— 基础 Agent 典型失败案例对照自查。

## Phase 3 — 写作与登记（Agent 核心工作）

按顺序写 5 个文件。**先证据、后行文**。

### 3.1 写 /app/work/evidence_map.json

从 fact_candidates.jsonl 中采信条目（可合并、可改写 quote，但数字必须与原材料一致），登记本稿实际用到的证据：

```json
[
  {"eid": "E1", "type": "finding", "source": {"kind": "note", "loc": "N1"},
   "quote": "未改性样品暴露 1 小时后电导率下降约 40%", "numbers": ["1", "40%"], "note": "Yao 2021 综述数据"}
]
```

- type ∈ finding | limitation | result | meta | judgment。judgment 仅用于作者判断（无法落到材料时）。
- source.kind ∈ manuscript | note | library；loc 用候选中的 pid（P###）/ nid（N###）/ entry id（R###）。
- 规模控制：8–20 条。每条 quote ≤200 字。

### 3.2 写 /app/work/draft_intro.md（引言工作稿）

固定结构（标题文字可微调，三组二级标题必须有）：

```markdown
# 引言

## 研究背景与问题
<2–4 段：领域脉络（带锚点）→ 具体矛盾（带锚点）→ 具体未解决问题（必须出现
"尚未/仍缺乏/有待/瓶颈"类表述）。每句具体事实论断句末挂 〔E#〕。>

## 研究空白
<1 段：由已引工作的缺口推出（此处句子的锚点指向 limitation 类证据）。>

## 本文贡献
<1 段或条目式：每条贡献注明证据位置（P###/图N/表N），句末挂 〔E#〕。>

## 章节安排（可选）
```

写作要求（违反将被引擎或评审判负）：

- **禁句**（空转铺垫，见 anti_fluff_patterns.txt）："近年来受到广泛关注""随着……的快速发展"
  "具有重要意义""不可或缺"等；背景第一句必须从领域具体事实或矛盾起笔。
- 语言：正式中文书面语，全文用"本文/本工作"，禁止"我/我们/你"；全角标点，枚举用顿号；
  首次出现的术语与缩写给出全称（如 人工智能（AI））。
- 数字必须与 evidence_map quote 中一致；不得新增材料外数字。
- 篇幅：引言正文 400–900 字。

### 3.3 写 /app/work/draft_rl.md（相关工作工作稿）

```markdown
# 相关工作

## <分组主题1：按方法路线/问题设定命名>
<一段或多段：同组工作在同一维度上比较，句末挂 〔E#〕。>

## <分组主题2>
...
```

- 按路线分组，不按时间罗列；每组先给一句组内共性与差异，再逐工作准确转述结论与局限。
- 篇幅 400–1000 字；引用 5–15 篇（以材料为准，不得臆造）。

### 3.4 写 /app/work/claim_bindings.jsonl（论断-引用绑定，每行一条 JSON）

```json
{"loc": "intro", "sentence": "<工作稿中逐字存在的论断句（含或不含 〔E#〕 均可）>", "entry_ids": ["R002"], "eids": ["E3"], "claim_type": "others_result"}
```

- loc ∈ intro | rl；claim_type ∈ others_result | quantitative_fact | method_lineage | survey_coverage | comparison | own_result。
- entry_ids 必须存在于 library.json；eids 必须存在于 evidence_map.json。
- 每个挂锚点的事实句至少一条 binding；纯过渡句（claim_type=transition 可不写 binding）除外。

### 3.5 本版本专属：背景锚定自检表（写入 /app/work/version_notes.md）

写 4 行以内：背景段锚定句数/总句数；检出的空转句及替换决定；未解决问题句的位置；
judgment 类证据的条目号。这是 anti_fluff.py 审计的人工侧写，供评审对照。

### 3.6 登记不确定性与异常（按需）

- `/app/work/uncertainty.json`：[{"item", "reason", "impact"}] —— 材料冲突、来源存疑、判断类论断。
- `/app/work/exceptions.json`：材料缺失、解析失败、文献库为空等。

## Phase 4 — 引擎核验与构建

```bash
python3 /skills/weekly-skill/scripts/anti_fluff.py --work /app/work --out /app/output --patterns /skills/weekly-skill/references/anti_fluff_patterns.txt
python3 /skills/weekly-skill/scripts/build_deliverables.py --work /app/work --out /app/output
```

- 读 `/app/output/build_report.json`：锚点必须全部 resolved；绑定 matched/total ≥ 90%；
  四要素背景/空白/贡献/分组全 true；agent_pre_numbered 为空。
- 读 `/app/output/anti_fluff_audit.md`：verdict=pass 最佳；warn 时按改写建议修改 draft_intro.md 后重跑；
  fail 必须修复后再交付。
- **允许一次修复循环**：改工作稿 → 重跑 Phase 4 两条命令。仍有问题则如实降级 status。

收尾（无论成功与否必跑）：

```bash
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --case /input/case.json --skill "library-salvage v2.0.1" --status <success|partial>
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --expect-status <success|partial>
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```

## Phase 5 — 状态判定

- `success`：四要素全、锚点全解析、绑定 ≥90% 命中、anti_fluff verdict ∈ {pass, warn}、
  无 unresolved critical exception。
- `partial`：上述任一项不满足但已交付可用稿件。必须在 result.json 的 exceptions/uncertainty 写明缺什么、
  影响什么、建议人工如何补。
- 禁止 `failed` 空交：至少保留骨架 result.json + 已写出的任何工作稿副本（cp 到 /app/output）。

## 异常处置表

| 情况 | 处置 |
|---|---|
| 无稿件（只有题目+文献） | 背景/相关工作可写；贡献部分标"材料缺口"，result 标 partial |
| 文献库为空 | 先跑 salvage_library.py 抢救；抢救成功照常引用（低置信条目记 uncertainty）；抢救失败才降级 partial |
| 笔记缺失 | 以稿件+文献库元数据为证据来源；在 version_notes 说明 |
| 绑定句定位失败 | 引擎报 missed；逐字核对句子后修复，禁止手写编号绕过 |
| 输出契约含未知字段 | assemble_result 自动回填别名；仍缺则在 --field 补充 |
| 模型请求 >40 或耗时 >600s | 立即跳过修复循环，以现状跑 Phase 4 收尾，status=partial |
| 任务书语言为英文 | 全文用英文写作；标点英文规范；文献表同规则渲染 |

## 交付物清单（/app/output）

`introduction.md`、`related_work.md`、`references.md`、`evidence_map.json`、`build_report.json`、
`anti_fluff_audit.md`、`version_report.json`（引擎审计）、`result.json`（含 output_contract 全部字段回填）、
`preview.html`。所有 .md 可继续编辑；result.json 如实记录 status、来源与不确定性。
