# CHANGELOG

## v2.0.4（2026-11-24）

- 版本性质：v2.0.0（attempt 101508）因平台侧 JudgeUnavailable 未获评分（harbor_errors=0，
  非 Skill 缺陷）；本版以唯一最高分已出分版本 v1.0.4（90655，55 分）为父版，
  原样复投同一最高预期增益机制，机制内容与 v2.0.0 等价，代理 case 回归复测通过。
- 改了啥（相对父版 v1.0.4 的唯一机制改动）：新增 scripts/instruction_audit.py + direction.json——
  题面指令原子化清单（work/instruction_checklist.json）与交付前落实审计
  （work/instruction_report.json）；error 级 fail 为交付硬闸；
  assemble_result.py 的 REPORTS 清单追加两个报告文件名（契约键名结构零改动）。
- 没动啥：其余 9 个脚本、SKILL.md 流程主体、references、result.json 契约字段全部原样。
- 真跑动机：基线 v1.0.4 代理 case 中漏检"题面指定 pdflatex"约束（实选 xelatex 无人发现）。

## v1.0.4（2026-11-19）

- 首版：模板适配与可重复构建方向。
- template_audit.py：P1 类必填元数据（内置 IEEEtran/elsarticle/acmart/ctexart 等表）、
  P2 五组宏包冲突对、P3 hyperref/cleveref 加载顺序、P4 过时宏包与声明式字体命令、
  P5 模板差异比对（缺载宏包/规定 .bst）。
- build_manifest.py：真实 --version + 日志宏包版本 + 源码 sha256 + 精确命令序列，
  生成机读 build_manifest.json 与人读 BUILD_MANIFEST.md。
- 共享核心与编译验证闭环同 v1.0.0。
