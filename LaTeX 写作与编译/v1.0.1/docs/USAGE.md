# 使用说明（latex-math-consistency v1.0.1）

## 输入 / 输出

输入：/input/case.json（case_id + output_contract）、/input/task.md、材料（.tex 工程或论文 PDF）。
输出：/app/output/result.json（契约字段齐全）、latex_project/（可编辑源码）、
preview.pdf、reports/（inspection、build_report、math_report、source_check、change_log 等）。

## 步骤

1. 保底 init_result.py；侦察 inspect_case.py；把 task.md 的公式要求抄成 work/task_items.md。
2. 基线 tex_build.py（编译不过先修编译，数学模式错误按 references/math_rules.md 处置）。
3. 普查 math_audit.py → work/math_report.json；tex_check.py 复核交叉引用。
4. 一致性核对（Phase 2）：编号叙述、符号唯一性、公式数值与材料一致性。
5. 分批修复（每批 ≤5 处，改完复编 + 复扫 math_audit，findings 数下降为进度信号）。
6. 双通道验证：final 编译收敛 + math_report warn 清零或登记。
7. 交付：写 evidence_map/change_log/uncertainty 等 → assemble_result.py → validate_output.py。

## 自查

- validate PASS；build.final.success 与 converged 如实；
- math_report.json 的 warn 级 findings 为 0 或逐条见于 uncertainty；
- change_log 每条含 file/line/before/after/evidence（evidence 指向 math_report finding 或材料位置）。

## 失败处理

脚本均可安全重跑（幂等）；无引擎时仅静态交付 partial；预算过半立即走交付流程。
