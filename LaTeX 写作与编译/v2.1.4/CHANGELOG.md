# CHANGELOG

## v2.1.4（2026-11-25）

- 唯一机制改动（相对父版 v1.0.4，attempt 90655=55 分）：新增 math_audit.py（M1-M8 公式专项机检，只诊断不擅改）+ references/math_rules.md。
- 动机：题面「改得对」维度明确考察公式符号与编号，基线无任何公式级机检。

## v1.0.4（2026-11-19）

- 首版：模板适配与可重复构建方向。
- template_audit.py：P1 类必填元数据（内置 IEEEtran/elsarticle/acmart/ctexart 等表）、
  P2 五组宏包冲突对、P3 hyperref/cleveref 加载顺序、P4 过时宏包与声明式字体命令、
  P5 模板差异比对（缺载宏包/规定 .bst）。
- build_manifest.py：真实 --version + 日志宏包版本 + 源码 sha256 + 精确命令序列，
  生成机读 build_manifest.json 与人读 BUILD_MANIFEST.md。
- 共享核心与编译验证闭环同 v1.0.0。
