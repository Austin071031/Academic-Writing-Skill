---
name: methods-element-phase-matrix
description: >-
  六要素阶段矩阵：方法与实验章节按"要素×训练/验证/测试"矩阵驱动写作，专治写得全与条件串台。
  当用户提供论文 PDF、配置、日志、代码等材料要求"撰写/补写方法与实验章节、整理实验设置、
  把零散实验记录整理成步骤序列"时触发；亦适用于需要分别描述训练/验证/测试流程、防止条件
  串台（训练超参写进评测、验证集口径混入测试）的修复场景。不触发：纯结果复现计算、全文
  润色、文献管理。产出物：methods_chapter.md（七节成稿）、element_matrix.json
  （18 格覆盖矩阵）、matrix_report.json（串台检测报告）、provenance_map.json、
  build_report.json 与 result.json（含缺口、人工确认项与不确定性）。
---

# v1.0.1｜六要素阶段矩阵（要素×阶段 18 格覆盖 + 条件串台检测）

核心分工：**Agent 做矩阵登记与行文**（判定每格证据归属、把格子翻译成段落）；**确定性引擎做
矩阵完整性校验与串台检测**（18 格覆盖、参数 scope 标注、评测小节训练超参出现检测）。
章节不是从"Introduction 式"行文出发，而是从 6 要素 × train/val/test 的矩阵出发：
每一格要么有证据锚点与正文位置，要么显式登记"不适用 + 理由"。

## 三条红线

1. **不跳格**：18 格（步骤/设置/参数/数据集/对照/复现 × 训练/验证/测试）逐格登记；
   材料不支持的格子写 na+理由，不得整列留白。
2. **不串台**：训练专属条件（学习率、batch size、epoch 等）不得出现在评测/测试描述中；
   每个参数 scope 必须可判定阶段，engine 检测违规即 fail。
3. **不臆造**：矩阵每格的证据锚点须存在于采信台账；缺口进 gaps.json 并在附录C追问。

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

读 `work/inspection.json` 与 `work/evidence_candidates.jsonl`；对候选逐条回原文核对。

## Phase 2 — 读本版本方法规则

依次读（都在 `/skills/weekly-skill/references/` 下）：

1. `method_rules.md` —— 18 格登记语法、na 理由规范、串台判定标准 + 失败模式对照；
2. `templates.md` —— 每格事实粒度清单、scope 标注规范、缺口分级与追问。

## Phase 3 — 矩阵登记与行文（Agent 核心工作）

先矩阵、后段落：

1. 写 `work/element_matrix.json`：对 6 要素 × 3 阶段逐格登记
   `{"eids": ["E0005"], "section_anchor": "sections/03_params"}`；材料不覆盖则
   `{"na": true, "reason": "验证集仅用于早停，无独立超参"}`。
2. 写 `work/sections/01_steps.md`…`07_limitations.md` 七节正文（写法同骨架版：一句一事实、
   挂 〔E#〕；第二节必须把训练/验证/测试三段分开写）。
3. 写 `work/table_rows.json`（scope 必填）、`gaps.json`、`changes.json`、`status.json`、
   `contract_extra.json`。

## Phase 4 — 矩阵校验、装配与检测

```bash
python3 /skills/weekly-skill/scripts/element_matrix.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/build_deliverables.py --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work --expect-status success
```

- matrix 报告缺格或串台 flag 非空时：补登记/改写后再装配；确属材料问题的进 gaps 并降级。
- 章节"5 对照实验"小节引用实验行、参数 scope 含混都会在此阶段被拦下。

## Phase 5 — 如实定态

存在未解决 high/medium 缺口 → status="partial"；全部闭合 → "success"。
result.json 保留全部契约字段（含 output_contract 注入字段）。

## 异常处置

| 情况 | 处置 |
|-|-|
| 材料只有训练流程、无验证/测试描述 | val/test 列全格 na+理由；gaps(high) 追问评测协议；partial |
| 参数在多个阶段取值不同 | 每阶段单独一行 table_rows，scope 分开，正文分句写 |
| 日志显示实际运行条件与配置意图不同 | 训练格以日志为准，配置值进 changes 留痕 |
| 900 秒预算告急 | 立即跑 Phase 4 交付 partial（矩阵缺格也先落报告） |

## 最小调用示例

见 `examples/minimal_example.md`（合成材料，标注为示例）。
