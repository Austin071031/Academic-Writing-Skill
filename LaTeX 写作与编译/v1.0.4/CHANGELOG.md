# CHANGELOG

## v1.0.4（2026-11-19）

- 首版：模板适配与可重复构建方向。
- template_audit.py：P1 类必填元数据（内置 IEEEtran/elsarticle/acmart/ctexart 等表）、
  P2 五组宏包冲突对、P3 hyperref/cleveref 加载顺序、P4 过时宏包与声明式字体命令、
  P5 模板差异比对（缺载宏包/规定 .bst）。
- build_manifest.py：真实 --version + 日志宏包版本 + 源码 sha256 + 精确命令序列，
  生成机读 build_manifest.json 与人读 BUILD_MANIFEST.md。
- 共享核心与编译验证闭环同 v1.0.0。
