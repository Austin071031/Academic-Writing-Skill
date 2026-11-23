# 评测契约（§2.4，改错就 0 分；§0-8：本迭代不改契约层）

出处：赛题 API Harbor 技术提交约定（01_task_spec.md 同页）+ 基线 v1.0.4 脚本实现。

| 项 | 约定 | 出处 |
|-|-|-|
| Skill 安装路径 | /skills/weekly-skill（SKILL.md + 文本资源） | "The evaluator installs the actual Skill under /skills/weekly-skill" |
| 输入 | /input/case.json、/input/task.md + 材料；PDF 案例给真实 PDF（无预抽答案层） | "original input is /input/case.json and task.md … PDF parsing receives the actual PDF" |
| 工作目录 | /app/work | "Work under /app/work" |
| 交付目录 | /app/output；必须含 result.json（case_id + output_contract 全部字段，键名结构不改） | "including result.json with all original output_contract fields and case_id" |
| 产物形态 | 可编辑 .tex 源码工程；真实渲染的 PDF 预览；诚实 status/sources/uncertainty/change records；partial 必须写明 limits | "Editable … outputs should also have real rendered PDF/PNG previews … A partial result must identify its limits" |
| 预算 | 64 模型请求 / 900 秒 / 16384 token 每响应；3 案例 ×3 重复 | "Execution budget: 64 model requests, 900 seconds, 16384 tokens per response" |
| Skill 资源 | ≤50 个 UTF-8 文本文件、单文件 ≤500KB、总 ≤2MB、无符号链接 | "Skill resources: at most 50 UTF-8 text files, 500KB each and 2MB total, no symlinks" |
| 依赖 | 未明文限制；基线实现仅用 Python3 标准库 + 系统 TeX 工具（pdflatex/xelatex/bibtex/biber/latexmk），pdftotext 视环境探测后降级 | 基线 v1.0.4 scripts（实现事实） |
| 降级约定 | status ∈ success/partial/failed；failed 必须写清 exceptions；材料缺失/无法判断/运行失败分别说明 | "材料缺失、无法判断和运行失败要分别说明" + 基线 validate_output.py |
| 禁做 | 预制答案、臆造分数、臆造软件状态与科学数据 | "Do not submit prepared answers … do not invent benchmark scores. Do not fabricate…" |

## result.json 顶层字段（基线实现，v2.x 一律不改）

`case_id, status, skill, generated_at, task_summary, outputs, build, evidence_map,
change_log, uncertainty, manual_confirmations, exceptions, stats, sources,
output_contract_fields` + case.json 的 output_contract 各字段（动态键，原样透传）。

## 交付物目录形态（基线实现）

`/app/output/result.json`、`/app/output/latex_project/`（可编辑源码，剔除 aux 类中间文件）、
`/app/output/preview.pdf`、`/app/output/reports/`（inspection/build_report/log_report/
source_check/template_report/build_manifest/change_log 等 JSON 与 BUILD_MANIFEST.md）。
