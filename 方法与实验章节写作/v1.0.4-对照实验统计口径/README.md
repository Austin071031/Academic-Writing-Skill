# methods-baseline-comparability v1.0.4｜对照实验与统计口径

以实验矩阵（变体×数据集×划分×指标×预算×种子×重复×结果）为骨，可比性闸门强制
"同数据集/同划分/同指标/同预算或写豁免"，统计口径强制"多次给离散度、单次须声明"，
结论措辞按 表明/初步表明/有望 三档校准。让"与基线比较"成为可比结论而不是断言。

## 依赖与安装

- 仅 Python 3.8+ 标准库；`pdftotext` 用于 PDF 文本化（缺失自动降级并留痕）。
- 安装：整体复制到 `/skills/weekly-skill`；本地以本目录为根。

## 快速开始

Phase 0–1 同骨架版；Phase 3 写 `experiment_matrix.json` 与第五节 R# 引用；Phase 4 依次
`exp_matrix.py → build_deliverables.py → render_previews.py → validate_output.py`。
命令逐字见 SKILL.md 与 [docs/USAGE.md](docs/USAGE.md)。

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、材料文件。
- 输出（`/app/output`）：`methods_chapter.md`（含三附录）、`comparability_report.json`、
  `experiment_matrix.json`（work 与 output 各留一份）、`provenance_map.json`、
  `build_report.json`、章节预览、`result.json`。

## 适用边界

- 适用：对照实验小节撰写/核查、基线比较可比性审计、统计口径规范化。
- 不适用：真实重跑实验、全文润色、文献管理。
- partial 规则：可比性问题未解决或基线数值缺失即 partial。

## 维护信息

- 版本 v1.0.4（2026-11-19）；变更见 CHANGELOG.md；自查表见 evaluation/scoring_sheet.md。
