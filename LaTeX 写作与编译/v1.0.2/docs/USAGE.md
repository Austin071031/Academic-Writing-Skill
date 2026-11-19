# 使用说明（latex-table-governance v1.0.2）

## 输入 / 输出

输入：/input/case.json、/input/task.md、材料（.tex 工程或论文 PDF）。
输出：/app/output/result.json（契约字段齐全）、latex_project/（可编辑源码）、
preview.pdf、reports/（table_report、build_report、log_report、fix_log、change_log 等）。

## 步骤

1. 保底 init_result.py；侦察 inspect_case.py；任务表格要求抄成 work/task_items.md。
2. 基线 tex_build.py（编译先修通）；普查 table_audit.py → work/table_report.json。
3. 机械修复：table_audit.py --apply-booktabs --apply-float-htbp；复编译确认；
   若报 \toprule 未定义，补 \usepackage{booktabs}。
4. 语义修复：按 T3/T5/T7/T8 findings 逐表处置（判据 references/table_rules.md），
   每表改完复编；数据问题只依材料，不明记 uncertainty。
5. 验证：final 编译收敛 + table_audit 复扫 + log_report 无 >20pt overfull。
6. 交付：写 evidence_map/change_log/uncertainty 等 → assemble_result.py → validate_output.py。

## 自查

- validate PASS；table_report error 级清零、warn 级清零或逐条登记；
- fix_log（机械）与 change_log（人工）分离且每条可回溯；
- preview.pdf 目视核对重点表格页（启发式报警的确认证据）。

## 失败处理

脚本幂等可重跑；booktabs 不可用时退回 \hline 并记 uncertainty；预算过半立即交付。
