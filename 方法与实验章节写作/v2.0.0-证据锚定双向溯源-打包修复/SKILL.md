---
name: methods-evidence-anchoring
description: >-
  证据锚定双向溯源：方法与实验章节的逐条证据锚定与"写得准"审计。当用户提供论文 PDF、
  配置文件、实验日志、代码等材料，要求"撰写/补写方法与实验章节、整理实验设置、把零散
  实验记录写成方法章节"时触发；亦适用于需要核查章节中每个数值是否来自材料、是否存在
  "为段落顺畅而补出的数值"的场景。不触发：纯结果复现计算、全文语言润色、与章节写作
  无关的文献管理。产出物：methods_chapter.md（七节成稿，句中 〔E#〕 为证据锚点）、
  provenance_map.json（证据台账）、audit_report.json（双向溯源审计）、
  build_report.json 与 result.json（含缺口、人工确认项与不确定性）。
---

# v1.0.0｜证据锚定双向溯源（章节断言 ↔ 证据台账 双向审计）

核心分工：**Agent 只做判断与写作**（采信证据、写步骤句、定缺口归属）；**确定性引擎做全部
机械劳动与核验**（材料清点、PDF 按页文本化、要素候选抽取、锚点解析、附录装配、双向溯源审计）。
本章的每一句含数值/参数/条件的断言都必须挂 〔E#〕 证据锚点；找不到证据的只写进附录C缺口
清单，不得硬写进正文。

## 三条红线

1. **不臆造数值**：正文每个数字必须能在 provenance_map.json 某条 quote/value 中找到；
   audit_provenance.py 做正向泄漏检查，泄漏即 fail，必须改写或补证据。
2. **采信须双向闭合**：被采信进台账的每条证据，要么被正文引用，要么在
   work/unused_evidence.json 登记未使用理由；反向检查不过须补引或说明。
3. **缺口不隐藏**：材料缺失、来源冲突、需作者确认的内容一律进 gaps.json → 附录C与
   result.json 的 uncertainty/manual_confirmations，status 如实降级。

## 环境与路径约定

- 输入：`/input/case.json`、`/input/task.md` 与材料文件（PDF / yaml,json,toml,ini 配置 /
  log,out 日志 / py,sh,ipynb 代码 / md,txt 文档）。
- 工作目录 `/app/work`，最终产物 `/app/output`（必须含 `result.json`）。
- 本 Skill 安装于 `/skills/weekly-skill`，命令一律用绝对路径 `python3 /skills/weekly-skill/scripts/xxx.py`。
- 预算：64 次模型请求 / 900 秒 / 每响应 ≤16384 token。Phase 3 是唯一模型密集阶段，控制在 25 次请求内。

## Phase 0 — 落盘骨架（防超时空手，无判断）

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
```

## Phase 1 — 侦查、解析与候选抽取

```bash
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 /skills/weekly-skill/scripts/extract_evidence.py --work /app/work
```

Agent 动作：读 `/app/work/inspection.json`，确认 case_id、output_contract_fields、materials
分类与 exceptions；读 `/app/work/evidence_candidates.jsonl`（要素候选，每条带 eid、来源文件、
页/行定位与原文摘录）。PDF 已由 inspect_case.py 用 pdftotext 按页文本化（`===== PAGE k =====`），
论文中的方法与实验陈述同样可定位到页。

## Phase 2 — 读本版本方法规则

依次读（都在 `/skills/weekly-skill/references/` 下）：

1. `method_rules.md` —— 采信、改写 quote、锚点语法与双向闭合规则 + 失败模式对照；
2. `templates.md` —— 六要素核对清单、附录A参数表字段、缺口分级与追问句式。

## Phase 3 — 写作与登记（Agent 核心工作）

**先证据、后行文**。在 /app/work 下写七个文件：

- `sections/01_steps.md`…`07_limitations.md` —— 章节七节正文。每节 3–8 句，一句一事实，
  含数值/参数/条件的句末挂 〔E#〕；无证据的内容不写进正文，移入 gaps。
- `evidence_used.json` —— 采信证据列表：候选 eid 字符串，或补充行 `{"eid":"A001","source":…,
  "locator":…,"quote":…,"value":…}`（用于候选未覆盖但材料中确有的事实；quote 必须与原文逐字一致）。
- `unused_evidence.json` —— 采信后未用的证据及理由（如"代码默认值，运行未采用"）。
- `table_rows.json` —— 参数表行（附录A）；`gaps.json` —— 缺口与追问；
  `changes.json` —— 你对材料数值做过的任何取舍记录（如"以日志实际值为准"）；
  `status.json` —— `{"case_id","status","task_summary","exceptions","stats","sources",
  "output_contract_fields"}`；`contract_extra.json` —— output_contract 要求但骨架没有的字段。

七节骨架（材料无对应内容时该节写"⚠ 材料不足"说明 + 进 gaps，不得省略）：

1. 方法步骤——有序步骤序列，每步输入/操作/输出，避免多步压成一句；
2. 实验设置——硬件、软件版本、运行环境、随机种子、重复次数；
3. 参数与来源——正文数值与附录A参数表一致；
4. 数据集与划分——名称、版本、规模、预处理、划分比例与随机方式、子集用途；
5. 对照实验——基线及版本、是否同预算、指标与统计方式；
6. 可复现清单——代码版本、环境、命令、数据获取；
7. 限制条件与适用范围——落到具体失效场景。

## Phase 4 — 装配、审计与校验

```bash
python3 /skills/weekly-skill/scripts/build_deliverables.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/audit_provenance.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work --expect-status success
```

- 装配后章节含附录A参数表、附录B证据对照表（锚点→来源→位置→摘录）、附录C缺口清单。
- **audit 必须 verdict=pass** 才算 success；有泄漏就先修正章节或补采证据，无法补的改写到
  附录C并降级。validate 失败不得强行 success。

## Phase 5 — 如实定态

存在未解决缺口 → status="partial" 并在 result.json 说明限制；全部闭合 → "success"。
result.json 必须保留：case_id、status、outputs、evidence_map、change_log、uncertainty、
manual_confirmations、exceptions、stats、sources、output_contract_fields 及 output_contract
要求的全部字段（经 contract_extra.json 注入）。

## 异常处置（识别 → 处置）

| 情况 | 处置 |
|-|-|
| case.json 缺失/不可解析 | init_result 记录异常；case_id="unknown"；照常跑材料并在 exceptions 说明 |
| PDF 无法文本化（无 pdftotext/扫描件） | inspection 记录；改用 OCR 工具或仅依据配置/日志/代码写作并在 uncertainty 注明 |
| 某要素无任何材料 | 该节写材料不足说明 + gaps(high)；status=partial |
| 参数跨来源取值不同 | 以"日志实际运行值 > 配置值 > 代码默认值 > 论文正文转述"采信，changes 记录取舍，他值进 unused_evidence |
| 900 秒预算告急 | 立即运行 build+audit+validate 交付 partial（已有骨架兜底，不空手） |

## 最小调用示例

见 `examples/minimal_example.md`（合成材料，标注为示例，非正式案例结果）。
