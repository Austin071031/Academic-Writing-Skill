# CHANGELOG

## v2.1.2（2026-11-25）

- 改了啥（唯一机制改动）：新增 scripts/template_fix.py + direction.json——P1 必填项
  TODO 骨架/hyperref 顺序/过时宏包白名单三类受限自动修复；SKILL.md Phase 2 前置机械修复；
  assemble_result.py 的 REPORTS 追加 template_fix_log（契约键名结构零改动）。
- 没动啥：其余 9 个脚本、流程主体、references、result.json 契约字段全部原样。
- 动机：基线 template_audit 只审不修，必填项全靠 Agent 手工插入，效率与一致性双损。

## v1.0.4（2026-11-19）

- 首版：模板适配与可重复构建方向。
- template_audit.py：P1 类必填元数据（内置 IEEEtran/elsarticle/acmart/ctexart 等表）、
  P2 五组宏包冲突对、P3 hyperref/cleveref 加载顺序、P4 过时宏包与声明式字体命令、
  P5 模板差异比对（缺载宏包/规定 .bst）。
- build_manifest.py：真实 --version + 日志宏包版本 + 源码 sha256 + 精确命令序列，
  生成机读 build_manifest.json 与人读 BUILD_MANIFEST.md。
- 共享核心与编译验证闭环同 v1.0.0。
