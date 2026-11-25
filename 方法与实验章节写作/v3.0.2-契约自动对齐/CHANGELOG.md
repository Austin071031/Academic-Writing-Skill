# CHANGELOG

## v3.0.2（2026-11-25）方向迭代（父辈 v2.0.2 / attempt 101411 / 62.6667）

- 改了啥（唯一一件事）：契约自动对齐：init_result 自动推导 contract_extra 草稿；新增 contract_audit.py（task.md 原子指令拆解+装配后契约/指令覆盖校验）。改动文件：init_result.py、build_deliverables.py 加草稿合并；新增 scripts/contract_audit.py；SKILL.md 加 Phase 1.5 与 Phase 4 校验步。
- 没动啥：打包形态（≤50 文本文件）、SKILL.md 其余流程、其余脚本逻辑、输出契约
  （result.json 键名结构、产物清单、锚点语法）、repro_gate 引擎。
- 提分依据：父辈的 contract_extra.json 全靠 Agent 手写，字段映射错即 validate fail→partial；且章节结构不服从 task.md 指令。
- 回归证据：regression_report.json（资产/行为/契约守恒，3 代理 case 实测）。

## v2.0.2（2026-11-23）打包修复

- 改了啥（唯一一件事）：打包形态。删除 submission/ 镜像（13 文件）、docs/、evaluation/、
  GITHUB_URL.txt；references 5 文件合并为 2（method_rules.md + templates.md），SKILL.md Phase 2
  路径同步；新增 direction.json（build_deliverables.py 真实读取并写入 build_report.direction）。
  唯一文件 34→16，bundle 文本文件 ~68–80→42–46（<50 契约上限）。
- 没动啥：SKILL.md 三条红线与 Phase 0–5 流程、7 个脚本逻辑、规则/模板内容、输出契约
  （result.json 键名结构、产物清单、锚点语法）——回归证据见本目录 regression_report.json。
- 起因：v1 批次 5 次提交全部 evaluation_error（attempt 89818/89821/89823/89824/89826，
  platform_verified）；同窗口写作10 精简包 4/5 正常出分，旁证指向包内文本文件超 50。
- 提交：playground attempt 101411（product-arena-05-64faa4a2，方法与实验章节写作）
- 提交：playground attempt 106224（product-arena-05-64faa4a2，方法与实验章节写作）
