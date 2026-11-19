# 使用说明（latex-citation-convergence v1.0.3）

## 输入 / 输出

输入：/input/case.json、/input/task.md、材料（.tex 工程含 .bib，或论文 PDF）。
输出：/app/output/result.json（契约字段齐全）、latex_project/（可编辑源码含整理后
.bib）、preview.pdf、reports/（cite_report、build_report、source_check、change_log 等）。

## 步骤

1. 保底 init_result.py；侦察 inspect_case.py（读 tex_project.bib：backend/样式/文件）；
   任务引用要求抄成 work/task_items.md。
2. 基线 tex_build.py；重点看 build_report.passes 是否含 bib 工具轮（没有 = 链路断裂）。
3. 普查 cite_audit.py → work/cite_report.json（C1-C6）。
4. 处置：链路（backend 匹配）→ 悬空键（近似比对/材料补全/登记）→ 条目治理
   （去重合并、字段补全、未引用条目按任务处理）；每批复编。
5. 收敛：cite_audit.py --converge 驱动多轮编译；复扫 cite_audit + tex_check。
6. 交付：写 evidence_map/change_log/uncertainty 等 → assemble_result.py → validate_output.py。

## 自查

- validate PASS；cite_report error 级（C1/C5/C6）清零；
- converged 状态如实；未收敛项逐条见于 uncertainty；
- 合并条目在 change_log 有 keep/drop/rationale；PDF 末页参考文献表目视存在。

## 失败处理

bibtex/biber 缺失时静态交付 partial；样式文件缺失换可用样式并记 uncertainty；
合并判据不足不合并；脚本幂等可重跑。
