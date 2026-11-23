# 表 3 · 版本骨架对照（LaTeX 写作与编译/ 实际目录读取，2026-11-23）

## 共有文件（全部 5 版一致，= 基线资产白名单取数依据）

```
SKILL.md  README.md  CHANGELOG.md  SUBMISSION.md
docs/USAGE.md  examples/minimal_example.md  evaluation/scoring_sheet.md
references/failure_modes.md
scripts/init_result.py      # 开跑即落盘 result.json 骨架（case_id + output_contract 字段）
scripts/inspect_case.py     # 侦察 case.json/task.md/材料，识别主文件/引擎/缺失引用，暂存工程
scripts/tex_build.py        # 多轮编译封装：引擎探测/bib 链路/收敛判断/超时保护
scripts/tex_logscan.py      # 日志解析：19 类错误分类 + file:line + 级联根因归并
scripts/tex_check.py        # 源码静态审查：交叉引用/bib 键/环境配平/占位符/元数据
scripts/assemble_result.py  # 契约化交付：latex_project + preview.pdf + reports + result.json
scripts/validate_output.py  # 交付闸门：契约字段/case_id/可编辑产物核查
```

## 各版独有文件

| 版本 | 独有脚本 | 独有 references | 方向 |
|-|-|-|-|
| v1.0.0 | scripts/safe_fix.py（白名单机械修复） | error_taxonomy.md、fix_playbook.md | 编译得通 |
| v1.0.1 | scripts/math_audit.py（M1-M7 公式普查） | math_rules.md | 改得对·公式 |
| v1.0.2 | scripts/table_audit.py（T1-T8 表格体检） | table_rules.md | 改得对·表格 |
| v1.0.3 | scripts/cite_audit.py（C1-C6 引用审查 + --converge） | citation_rules.md | 引用收敛 |
| v1.0.4 | scripts/template_audit.py（P1-P5 模板审计）、scripts/build_manifest.py（构建清单） | template_rules.md | 模板适配+复现 |

## 观察

- 5 版均无 `direction.json`（§4-11 新机检参数要求从 v2.0.0 起补齐）。
- 5 版均无 PDF 文本抽取工具（PDF-only 案例路径只有文字说明，无脚本）。
- 5 版 SKILL.md 均为 Phase 0-5 长流程，无"最小闭环快速通道"；
  两个已出分 attempt（90654/90655）outcome 均为 partial（platform_verified）。
- index_drift：根 README 索引只有 v1.0.0–v1.0.4 一行，与目录一致（无 drift）；
  但平台另有 4 次外部提交（见 01_attempt_registry.md）。
