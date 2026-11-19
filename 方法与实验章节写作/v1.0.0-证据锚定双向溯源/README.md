# methods-evidence-anchoring v1.0.0｜证据锚定双向溯源

将散落的论文 PDF、配置、日志、代码整理成**逐条可回溯**的方法与实验章节：正文断言挂 〔E#〕
证据锚点，确定性引擎做正向泄漏检查（正文数值必须来自材料）与反向闭合检查（台账证据必须
被使用或说明理由），材料缺口全部显式登记并追问作者。

## 依赖与安装

- 仅 Python 3.8+ 标准库；`pdftotext`（poppler）用于 PDF 文本化，缺失时自动降级并在
  result.json 的 exceptions 留痕。
- 安装：将本目录整体复制到 `/skills/weekly-skill`（平台执行）；本地开发直接以本目录为根。
- 无网络依赖、无第三方包、无个人文件依赖。

## 快速开始（Agent 视角）

1. `python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output`
2. `python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work`
3. `python3 /skills/weekly-skill/scripts/extract_evidence.py --work /app/work`
4. 按 SKILL.md Phase 2–3 读规则、写 `work/sections/*.md` 与台账文件。
5. `build_deliverables.py` → `audit_provenance.py` → `render_previews.py` → `validate_output.py`。

完整说明见 [docs/USAGE.md](docs/USAGE.md)；合成最小示例见 [examples/minimal_example.md](examples/minimal_example.md)。

## 输入 / 输出

- 输入：`/input/case.json`（case_id、output_contract）、`/input/task.md`、材料文件。
- 输出（`/app/output`）：`methods_chapter.md`（含附录A参数表/B证据对照/C缺口清单）、
  `provenance_map.json`、`audit_report.json`、`build_report.json`、`methods_chapter_preview.pdf|txt`、
  `result.json`（含 output_contract 全部字段、case_id、status、uncertainty、manual_confirmations、
  change_log、exceptions）。

## 适用边界

- 适用于：方法/实验章节撰写、补写、核查"写得全、写得准"。
- 不适用于：需要真实重跑训练/实验的复现任务、全文润色、文献管理。
- 部分结果（partial）规则：high/medium 缺口未解决即 partial，并在 result.json 说明限制。

## 维护信息

- 版本：v1.0.0（2026-11-19）。变更见 CHANGELOG.md。
- 评分维度自查表见 evaluation/scoring_sheet.md；本地冒烟材料见 evaluation/smoke_test.md。
