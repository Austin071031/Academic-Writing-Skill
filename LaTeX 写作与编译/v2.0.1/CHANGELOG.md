# CHANGELOG

## v2.0.1（2026-11-23）

- 改了啥（唯一机制改动）：新增 scripts/fast_lane.py + direction.json——最小闭环保底
  管线（六步一条命令，任一步失败不中止，partial 先落盘）；SKILL.md 新增强制 Phase F；
  assemble_result.py 的 REPORTS 追加 fast_lane_log.json（契约键名结构零改动）。
- 没动啥：其余 9 个脚本、Phase 0-5 细流程、references、result.json 契约字段全部原样。
- 平台动机：90654/90655 outcome 均为 partial（platform_verified），预算耗尽无保底。

## v1.0.4（2026-11-19）

- 首版：模板适配与可重复构建方向。
- template_audit.py：P1 类必填元数据（内置 IEEEtran/elsarticle/acmart/ctexart 等表）、
  P2 五组宏包冲突对、P3 hyperref/cleveref 加载顺序、P4 过时宏包与声明式字体命令、
  P5 模板差异比对（缺载宏包/规定 .bst）。
- build_manifest.py：真实 --version + 日志宏包版本 + 源码 sha256 + 精确命令序列，
  生成机读 build_manifest.json 与人读 BUILD_MANIFEST.md。
- 共享核心与编译验证闭环同 v1.0.0。
