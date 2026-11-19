# methods-element-phase-matrix v1.0.1｜六要素阶段矩阵

按 **6 要素 × train/val/test = 18 格** 矩阵驱动的方法与实验章节写作：每格登记证据锚点或
"不适用+理由"，确定性引擎校验矩阵完整性、参数阶段归属（scope）并检测条件串台
（训练超参混入评测描述）。专治"写得全"与"条件串台"两类高频问题。

## 依赖与安装

- 仅 Python 3.8+ 标准库；`pdftotext` 用于 PDF 文本化（缺失自动降级并留痕）。
- 安装：整体复制到 `/skills/weekly-skill`；本地以本目录为根。
- 无网络依赖、无第三方包。

## 快速开始

Phase 0–1 同骨架版（init → inspect → extract）；Phase 3 先写 `work/element_matrix.json`
再写七节正文；Phase 4 依次 `element_matrix.py → build_deliverables.py → render_previews.py
→ validate_output.py`。命令逐字见 SKILL.md 与 [docs/USAGE.md](docs/USAGE.md)。

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、材料文件。
- 输出（`/app/output`）：`methods_chapter.md`（含三附录）、`matrix_report.json`
  （18 格覆盖 + 串台检测）、`provenance_map.json`、`build_report.json`、章节预览、
  `result.json`（含 output_contract 全部字段与 case_id）。

## 适用边界

- 适用：章节撰写/补写；训练-验证-测试流程需要分开描述的场景；条件串台修复。
- 不适用：真实重跑实验的复现任务、全文润色、文献管理。
- partial 规则：矩阵缺格未解决或 high/medium 缺口未解决即 partial。

## 维护信息

- 版本 v1.0.1（2026-11-19）；变更见 CHANGELOG.md；自查表见 evaluation/scoring_sheet.md。
