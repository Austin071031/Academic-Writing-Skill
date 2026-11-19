# 使用说明（latex-compile-rescue v1.0.0）

## 输入

| 输入 | 位置 | 说明 |
|-|-|-|
| case.json | /input/case.json | 含 case_id 与 output_contract（契约字段清单） |
| task.md | /input/task.md | 任务说明：改动点、模板与格式约束 |
| 材料 | /input/ 其余文件 | .tex 工程（可能含 .sty/.cls/.bib/图片）或论文 PDF 等材料 |

## 输出

| 输出 | 位置 | 说明 |
|-|-|-|
| result.json | /app/output/result.json | 顶层含 case_id + output_contract 全部字段；status/evidence_map/change_log/uncertainty/manual_confirmations/exceptions/build 摘要 |
| 可编辑工程 | /app/output/latex_project/ | 修复后的 .tex/.bib/.sty/图片等源码（剔除 .aux 等中间文件） |
| PDF 预览 | /app/output/preview.pdf | 最终一轮编译产物（有引擎时） |
| 复核报告 | /app/output/reports/ | inspection/build_report/log_report/source_check/fix_log/change_log 等 JSON |

## 完整调用步骤

1. **保底**：`init_result.py` 落盘骨架 result.json（含契约字段与 case_id）。
2. **侦察**：`inspect_case.py` 解析输入、暂存工程到 /app/work/project、识别主文件与引擎。
3. **基线**：`tex_build.py --tag baseline --until-converge` 建立事实基线（错误数、
   是否收敛、引擎）。
4. **分诊**：`tex_logscan.py` 出根因假设与级联标记；`tex_check.py` 出源码级问题清单。
5. **修复**：`safe_fix.py` 做白名单机械修复；Agent 按 file:line 做语义修复并逐条记
   work/change_log.json；每修一批复编一次。
6. **验证**：`tex_build.py --tag final --until-converge` + `tex_check.py` 复核；
   对照 task_items.md 验收。
7. **交付**：写 evidence_map/uncertainty/manual_confirmations/exceptions/stats 后
   `assemble_result.py` + `validate_output.py`。

## 自查方法

- `validate_output.py` 打印 PASS 是交付底线。
- 结果正确性自查：build_report.final.success 与 converged、
  source_check 的 undefined_* 与 placeholders、log_report 的 overfull>20pt 清单。
- 可复核性自查：change_log 每条是否含 file/line/before/after/evidence；
  证据能否在 reports/ 的日志与 JSON 中找到。

## 失败处理

- 任何脚本异常退出：先看 stderr；脚本自身不修改已落盘的 JSON，可安全重跑（幂等）。
- 无 TeX 引擎：tex_build 如实报 exception；转 tex_check 静态审查，status=partial。
- 预算告急：见 SKILL.md 第 5 节，立即以当前最好状态走 Phase 5。
