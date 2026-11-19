# methods-reproduction-gate v1.0.2｜可复现命令链

以"读者能否照做"为轴的方法与实验章节写作：复现七要素（代码版本/环境/硬件/数据获取/
命令/种子/开销）逐项登记，确定性闸门校验完整性，并强制"每条命令必须出现在正文复现
小节"。限制条件一律写到具体失效场景。

## 依赖与安装

- 仅 Python 3.8+ 标准库；`pdftotext` 用于 PDF 文本化（缺失自动降级并留痕）。
- 安装：整体复制到 `/skills/weekly-skill`；本地以本目录为根。

## 快速开始

Phase 0–1 同骨架版；Phase 3 重点写 `work/repro_checklist.json` 与第六节命令代码行；
Phase 4 依次 `repro_gate.py → build_deliverables.py → render_previews.py → validate_output.py`。
命令逐字见 SKILL.md 与 [docs/USAGE.md](docs/USAGE.md)。

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、材料文件。
- 输出（`/app/output`）：`methods_chapter.md`（含三附录与第六节复现清单）、
  `repro_report.json`、`repro_checklist.json`（随 build 输出为机读清单）、
  `provenance_map.json`、`build_report.json`、章节预览、`result.json`。

## 适用边界

- 适用：章节撰写/补写、复现信息整理、限制条件具体化。
- 不适用：需要真实执行训练/评测的任务（本 Skill 只整理信息，不伪造运行）。
- partial 规则：复现七项缺任一项即 partial；命令未经日志确认时在 changes 注明。

## 维护信息

- 版本 v1.0.2（2026-11-19）；变更见 CHANGELOG.md；自查表见 evaluation/scoring_sheet.md。
