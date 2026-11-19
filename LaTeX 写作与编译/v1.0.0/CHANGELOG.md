# CHANGELOG

## v1.0.0（2026-11-19）

- 首版：编译错误诊断与迭代修复闭环。
- 共享核心：init_result / inspect_case / tex_build / tex_logscan / tex_check /
  assemble_result / validate_output（纯 Python3 标准库）。
- 方向专属：safe_fix.py（缺宏包白名单修复、引擎魔法注释、缺失 input 占位）。
- tex_logscan：19 类错误分类 + file:line 定位 + 级联根因归并 + Unicode 引擎错配识别。
- 本地合成案例端到端验证：基线 47 错（CJK+pdflatex）→ 换引擎 → booktabs 级联 →
  safe_fix → final 0 错；对真实悬空引用保持诚实的不收敛报告。
