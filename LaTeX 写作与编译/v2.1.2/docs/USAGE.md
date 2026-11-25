# 使用说明（latex-template-reproducible-build v2.1.2）

## 输入 / 输出

输入：/input/case.json、/input/task.md、材料（稿件 .tex 工程 + 目标模板 .cls/.sty/示例）。
输出：/app/output/result.json（契约字段齐全）、latex_project/（适配后可编辑工程）、
preview.pdf、reports/（template_report、build_report、BUILD_MANIFEST.md、
build_manifest.json、change_log 等）。

## v2.1.2 增量：模板合规受限自动修复

template_audit 之后运行 `python3 $S/template_fix.py --work /app/work --dry-run` 预演、
去 --dry-run 应用：自动处理 P1 必填项 TODO 骨架、hyperref 顺序、过时宏包替换；
TODO 骨架内容由 Agent 从材料回填（已登记 manual_confirmations）。

## 步骤

1. 保底 init_result.py；侦察 inspect_case.py（documentclass/packages/missing_refs）；
   识别模板材料路径，任务要求抄成 work/task_items.md。
2. 审计 template_audit.py --template <模板> → work/template_report.json（P1-P5）；
   基线 tex_build.py（编译先修通；缺 .cls 见 SKILL.md 异常表）。
3. 迁移适配：换类 → 必填项回填（内容只来自材料）→ 导言区整理（P2/P3/P4）→
   结构映射（摘要/关键词/参考文献机制）→ 删模板 dummy 内容；每批复编。
4. 收敛验证：final 编译 + tex_check + template_audit 复扫 + 目视 PDF 首页。
5. 构建清单：build_manifest.py → BUILD_MANIFEST.md（版本/命令/哈希/轮次）。
6. 交付：写 evidence_map/change_log/uncertainty 等 → assemble_result.py → validate_output.py。

## 自查

- validate PASS；template_report error 级清零；converged 如实；
- BUILD_MANIFEST 含真实版本（或 unknown 标注）、完整命令序列、全部源码哈希；
- 元数据回填均可回溯到稿件原文；占位项登记 manual_confirmations。

## 失败处理

模板类文件缺失→可用类兜底+uncertainty；版本不可得→unknown 标注；无引擎→静态审计
交付 partial 且 manifest 标注"未能编译验证"；脚本幂等可重跑。
