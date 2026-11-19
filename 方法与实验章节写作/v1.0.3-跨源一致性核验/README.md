# methods-cross-source-consistency v1.0.3｜跨源一致性核验

对配置/日志/代码/论文中同名参数的取值做机检冲突检测（数值归一化：3e-4 = 0.0003），
按"日志实际运行 > 配置实验意图 > 代码默认值 > 论文正文转述"三级优先级裁决，裁决
必须写规则与理由，无法判定的显式升级作者确认。专治"配置写 A、日志跑 B、论文写 C"。

## 依赖与安装

- 仅 Python 3.8+ 标准库；`pdftotext` 用于 PDF 文本化（缺失自动降级并留痕）。
- 安装：整体复制到 `/skills/weekly-skill`；本地以本目录为根。

## 快速开始

Phase 0–1 含 `cross_source_check.py --phase detect`（机检候选冲突）；Phase 3 写
`conflict_resolutions.json`；Phase 4 依次 `cross_source_check.py --phase verify` →
`build_deliverables.py` → `render_previews.py` → `validate_output.py`。
命令逐字见 SKILL.md 与 [docs/USAGE.md](docs/USAGE.md)。

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、材料文件。
- 输出（`/app/output`）：`methods_chapter.md`（含三附录）、`consistency_report.json`、
  `conflicts.jsonl`（work 与 output 各留一份）、`provenance_map.json`、`build_report.json`、
  章节预览、`result.json`（change_log 记录全部取舍）。

## 适用边界

- 适用：章节撰写/补写、参数核对、多源矛盾裁决。
- 不适用：真实重跑实验、全文润色、文献管理。
- partial 规则：存在 escalated 冲突即 partial。

## 维护信息

- 版本 v1.0.3（2026-11-19）；变更见 CHANGELOG.md；自查表见 evaluation/scoring_sheet.md。
