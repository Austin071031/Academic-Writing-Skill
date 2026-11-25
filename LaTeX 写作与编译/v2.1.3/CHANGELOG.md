# CHANGELOG

## v2.1.3（2026-11-25）

- 改了啥（唯一机制改动）：新增 scripts/pdf_extract.py + direction.json——PDF 材料
  直通（抽取→骨架重建→锚点映射→人工确认登记）；SKILL.md 新增 Phase 0.5；
  assemble_result.py 的 REPORTS 追加 pdf_report/rebuild_map（契约键名结构零改动）。
- 没动啥：其余 9 个脚本、主流程、references、result.json 契约字段全部原样。
- 真跑动机：基线在 PDF-only 代理 case 上 main=None 后全链停摆。

## v1.0.4（2026-11-19）

- 首版：模板适配与可重复构建方向。
- template_audit.py：P1 类必填元数据（内置 IEEEtran/elsarticle/acmart/ctexart 等表）、
  P2 五组宏包冲突对、P3 hyperref/cleveref 加载顺序、P4 过时宏包与声明式字体命令、
  P5 模板差异比对（缺载宏包/规定 .bst）。
- build_manifest.py：真实 --version + 日志宏包版本 + 源码 sha256 + 精确命令序列，
  生成机读 build_manifest.json 与人读 BUILD_MANIFEST.md。
- 共享核心与编译验证闭环同 v1.0.0。
