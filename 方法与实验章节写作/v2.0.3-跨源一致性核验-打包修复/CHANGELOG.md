# CHANGELOG

## v2.0.3（2026-11-23）打包修复

- 改了啥（唯一一件事）：打包形态。删除 submission/ 镜像（13 文件）、docs/、evaluation/、
  GITHUB_URL.txt；references 5 文件合并为 2（method_rules.md + templates.md），SKILL.md Phase 2
  路径同步；新增 direction.json（build_deliverables.py 真实读取并写入 build_report.direction）。
  唯一文件 34→16，bundle 文本文件 ~68–80→42–46（<50 契约上限）。
- 没动啥：SKILL.md 三条红线与 Phase 0–5 流程、7 个脚本逻辑、规则/模板内容、输出契约
  （result.json 键名结构、产物清单、锚点语法）——回归证据见本目录 regression_report.json。
- 起因：v1 批次 5 次提交全部 evaluation_error（attempt 89818/89821/89823/89824/89826，
  platform_verified）；同窗口写作10 精简包 4/5 正常出分，旁证指向包内文本文件超 50。
- 提交：playground attempt 101412（product-arena-05-64faa4a2，方法与实验章节写作）
