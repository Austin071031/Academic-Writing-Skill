---
name: methods-baseline-comparability
description: >-
  对照实验与统计口径：基线可比性闸门 + 实验矩阵 + 统计写法校准。当用户提供论文 PDF、
  配置、日志、代码等材料要求"撰写/补写方法与实验章节中的对照实验部分、整理基线与评测
  设置、检查与基线比较是否可比"时触发；亦适用于"同预算？同划分？同指标？重复几次？"
  类可比性核查与"优于基线"结论措辞校准的场景。不触发：真实重跑实验、全文润色、文献
  管理。产出物：methods_chapter.md（七节成稿，对照节按 R# 实验行引用）、
  experiment_matrix.json（实验矩阵）、comparability_report.json（可比性闸门）、
  provenance_map.json、build_report.json 与 result.json（含缺口、人工确认项与不确定性）。
---

# v1.0.4｜对照实验与统计口径（实验矩阵 + 可比性闸门 + 措辞校准）

核心分工：**Agent 建实验矩阵并行文**（从材料析出每个实验变体/基线的数据集、划分、指标、
预算、种子、重复次数与结果值）；**引擎做可比性闸门**（基线存在性、数据集/划分/指标一致
性、同预算、重复与统计口径、R# 被正文引用），并对"优于基线"类结论给出措辞校准规则。
专治"说得住"：与基线的比较是可比结论，不是断言。

## 三条红线

1. **不裸比较**：每个"优于/相当"结论对应实验矩阵中一行同数据集、同划分、同指标、
   同口径的对比；缺可比条件必须写差异或进 gaps。
2. **不造统计**：均值/方差/显著性只写材料支持的口径；单次运行必须声明"单次运行结果，
   未做显著性检验"；禁止编造 p 值或置信区间。
3. **不臆造数值**：基线结果数值没有材料支撑时，正文写"基线结果未在材料中给出"并进
   gaps(high) 追问，不得引用记忆里的"常见结果"。

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

读 `work/evidence_candidates.jsonl` 中 result/baseline/metric/split 类候选（acc、F1、
baseline 名、数据集与划分等）。

## Phase 2 — 读本版本方法规则

1. `statistics_style_rules.md` —— 实验矩阵字段、可比性判定、统计口径句式、结论措辞
   三档（表明/初步表明/有望）；
2. `six_elements_checklist.md`；3. `parameter_table_template.md`；
4. `gap_question_checklist.md`；5. `failure_modes.md`。

## Phase 3 — 矩阵登记与行文（Agent 核心工作）

1. 写 `work/experiment_matrix.json`：

```json
[{"rid": "R1", "variant": "Ours", "is_baseline": false, "dataset": "SynthBench v1.2",
  "split": "test", "metric": "Accuracy", "budget": "10 epochs", "seed": 42,
  "repeats": 1, "value": "0.913", "single_run_note": "单次运行", "source_eid": "E0020"},
 {"rid": "R2", "variant": "BERT-base", "is_baseline": true, "dataset": "SynthBench v1.2",
  "split": "test", "metric": "Accuracy", "budget": "10 epochs", "seed": 42, "repeats": 1,
  "value": "未在材料中给出", "single_run_note": "—", "source_eid": ""}]
```

- 不一致字段须加豁免键（如 `"dataset_waiver": "消融在子集上进行，原因见正文"`）。
- repeats>1 须给 mean 与 std/ci/sem；=1 须有 single_run_note。
2. 写七节正文；第五节逐行引用 R#（"本文方法（R1）…；BERT-base 基线（R2）…"）。
3. 写 `table_rows.json`、`gaps.json`、`changes.json`、`status.json`、`contract_extra.json`。

## Phase 4 — 可比性闸门、装配与校验

```bash
python3 /skills/weekly-skill/scripts/exp_matrix.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/build_deliverables.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work --expect-status success
```

- 闸门 fail：按 comparability_report.issues 补登记或写豁免；基线数值缺失进 gaps(high)。
- 结论措辞按 statistics_style_rules 校准后定稿。

## Phase 5 — 如实定态

存在未解决可比性问题或基线数值缺口 → status="partial"；否则 "success"。
result.json 保留全部契约字段。

## 异常处置

| 情况 | 处置 |
|-|-|
| 材料无基线信息 | gaps(high) 追问；第五节写"对照实验材料未提供" |
| 基线结果只有论文图里的一根柱（无数值） | 正文引用"图示约为 X"须带"读图估计"标注，或进 gaps |
| 多指标多划分 | 每行只填一对 (metric, split)，多对多行 |
| 重复次数材料未说明 | 按单次运行处理并追问；禁止默认"三次取平均" |
| 900 秒预算告急 | 立即跑 Phase 4 交付 partial |

## 最小调用示例

见 `examples/minimal_example.md`（合成材料，标注为示例）。
