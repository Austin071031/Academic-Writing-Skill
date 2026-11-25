---
name: methods-reproduction-gate
description: >-
  可复现命令链：以"读者能否复做"为轴的方法与实验章节写作。当用户提供论文 PDF、配置、
  日志、代码等材料要求"撰写/补写方法与实验章节、整理可复现信息、给复现清单"时触发；
  亦适用于需要补齐代码版本、环境、命令、随机种子、数据获取方式，或把限制条件写到具体
  失效场景的场景。不触发：真实重跑训练/实验、全文润色、文献管理。产出物：
  methods_chapter.md（七节成稿，第六节为复现清单）、repro_report.json（复现闸门）、
  repro_checklist.json（机读复现清单）、provenance_map.json、build_report.json 与
  result.json（含缺口、人工确认项与不确定性）。
---

# v1.0.2｜可复现命令链（章节为轴，命令为骨）

核心分工：**Agent 做信息归集与写作**（从材料找出版本/命令/种子/数据获取途径、写复现段落）；
**确定性引擎做复现闸门**（七项复现要素逐项检查 + 命令必须写进正文的校验）。
本版本把"做得着"置于中心：读者照章节第六节的清单即可逐步复做；缺一项，闸门 fail 或降级。

## 三条红线

1. **不缺复现项**：代码版本、环境（OS/Python/关键库）、硬件、数据获取（URL/校验和/路径）、
   命令序列、随机种子七项逐项登记；材料确实没有的进 gaps(high) 并降级，不留空项。
2. **命令必入章**：repro_checklist.json 登记的每条命令，其首个令牌必须出现在"6 可复现清单"
   小节正文里——清单不是摆设，读者在正文里就能抄到命令。
3. **限制落到场景**：限制条件必须写成"在 X 条件下失效/未验证"的具体句式，禁止
   "存在一定局限性"式套话；无来源的命令/版本号不得写进正文。

## 环境与路径约定

- 输入：`/input/case.json`、`/input/task.md`、材料文件（PDF/配置/日志/代码/文档）。
- 工作目录 `/app/work`，最终产物 `/app/output`（必须含 `result.json`）。
- 本 Skill 安装于 `/skills/weekly-skill`，命令一律绝对路径。
- 预算：64 次模型请求 / 900 秒 / 每响应 ≤16384 token；Phase 3 控制在 25 次请求内。

## Phase 0 — 落盘骨架

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
```

## Phase 1 — 侦查与候选抽取

```bash
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 /skills/weekly-skill/scripts/extract_evidence.py --work /app/work
```

读 `work/inspection.json`、`work/evidence_candidates.jsonl`；特别注意 extract 已抽出的
env_var（CUDA_VISIBLE_DEVICES 等）、command（日志中的启动命令）、version（框架/CUDA/库）
与 url（数据/代码获取地址）类候选。

## Phase 2 — 读本版本方法规则

依次读（都在 `/skills/weekly-skill/references/` 下）：

1. `method_rules.md` —— 七项登记格式、命令转录规范、失效场景句式 + 失败模式对照；
2. `templates.md` —— 各要素粒度清单、参数表、复现级缺口追问。

## Phase 3 — 行文与单一登记（Agent 核心工作，v3.0.0 减负版）

**只写两类文件**：七节正文 + 一个 registration.json。写完一节立即落盘，再写下一节（断点续跑：
任何时刻中断，build 都能用已落盘内容装配出合法产物）。

1. 写 `sections/01_steps.md`…`07_limitations.md` 七节正文（写法不变：一句一事实、挂 〔E#〕；
   第六节命令写成可复制代码行；第七节每条限制指向具体失效场景）。
2. 写**唯一**的登记表 `work/registration.json`，把所有登记项合并在一个文件里：

```json
{"evidence_used": ["E0005", "E0013"],
 "table_rows": [{"name": "learning_rate", "value": "3e-4", "unit": "—", "scope": "train", "source_eid": "E0005"}],
 "gaps": [{"element": "对照实验", "desc": "…", "severity": "high", "question_for_author": "…", "status": "unresolved"}],
 "changes": [{"change": "…", "reason": "…"}],
 "repro_checklist": {"code_version": "…", "environment": {"os": "…"}, "hardware": "…",
   "data_acquisition": {"path": "…"}, "commands": ["python train.py --config config.yaml"], "seeds": ["42"], "est_cost": "…"},
 "status": {"case_id": "<从 inspection.json 抄>", "status": "success|partial", "task_summary": "…",
   "exceptions": [], "stats": {}, "sources": {}, "output_contract_fields": ["<从 inspection.json 抄>"]},
 "contract_extra": {"<output_contract 要求的额外字段>": "<值>"}}
```

（分散的 table_rows.json/gaps.json 等旧写法仍被兼容，但不要再分开写——一次写入，一次请求。）

## 请求预算表（64 次模型请求总额，超支即跳 Phase 4）

| 阶段 | 预算 |
|-|-|
| Phase 0–1（跑 3 个脚本+读 inspection/candidates） | ≤6 |
| Phase 2（读 2 个 references） | ≤2 |
| Phase 3（写 7 节 + registration.json） | ≤12 |
| Phase 4（引擎+装配+校验+读报告+必要修正） | ≤15 |
| 预留（中断恢复/二次修订） | ≥20 |


## Phase 4 — 复现闸门、装配与校验

```bash
python3 /skills/weekly-skill/scripts/repro_gate.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/build_deliverables.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work --expect-status success
```

- repro_gate fail：缺项补材料依据或进 gaps 降级；命令未入章就改写第六节。
- 装配后第六节清单与正文命令一一对应；附录A参数表即复现抄表。

## Phase 5 — 如实定态

复现七项缺任一项未解决 → status="partial"（章节仍可用，但不可宣称完全可复现）；
全部闭合 → "success"。result.json 保留全部契约字段。

## 异常处置

| 情况 | 处置 |
|-|-|
| 材料无代码版本信息 | gaps(high) 追问仓库/commit；正文写"代码版本未在材料中给出" |
| 无网络获取地址，仅本地路径 | data_acquisition.path 登记相对路径+文件名+sha256（inspect 已算 head 哈希） |
| 日志缺启动命令 | 由配置与代码推演出等价命令并在 changes 注明"重构命令，未经日志确认" |
| 依赖版本不全 | environment.libs 写已确认项，缺失进 gaps(medium) |
| 900 秒预算告急 | 立即跑 Phase 4 交付 partial |

## 最小调用示例

见 `examples/minimal_example.md`（合成材料，标注为示例）。
