# methods-evidence-anchoring v2.0.0｜证据锚定双向溯源（打包修复版）

正文断言挂〔E#〕证据锚点；正向数值泄漏检查 + 反向台账闭合检查，双向不过即拦截。

## 与基线的唯一差异

本版 = v1.0.0-证据锚定双向溯源 的**打包修复**：v1 批次 bundle 内 UTF-8 文本文件约 68–80 个（outputs/+results/
双份 + submission/ 镜像），超出契约 "Skill resources: at most 50 UTF-8 text files"，5 次提交全部
evaluation_error（attempts 89818–89826，平台实查）。本版唯一文件收敛至 16（bundle 实测 42–46），
**内容与引擎零改动**：SKILL.md 流程、7 个脚本、规则与模板（合并为 references/ 2 文件）与基线一致。

## 依赖与安装

- 仅 Python 3.8+ 标准库；pdftotext 用于 PDF 文本化（缺失自动降级并在 result.json 留痕）。
- 安装：整体复制到 /skills/weekly-skill；无网络依赖、无第三方包。

## 调用步骤（Agent 视角，绝对路径）

0. `python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output`
1. `python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work`
   `python3 /skills/weekly-skill/scripts/extract_evidence.py --work /app/work`
2. 读 `references/method_rules.md` 与 `references/templates.md`
3. 按 SKILL.md Phase 3 写 work/sections/01..07_*.md 与台账文件（evidence_used/table_rows/gaps/changes/status/contract_extra + 方向登记表）
4. 方向引擎 → `build_deliverables.py` → `render_previews.py` → `validate_output.py --expect-status success`

完整流程、异常处置表见 SKILL.md；最小调用示例见 examples/minimal_example.md（合成材料，标注为示例）。

## 输入 / 输出

- 输入：/input/case.json、/input/task.md、材料文件（PDF/配置/日志/代码/文档）。
- 输出（/app/output）：methods_chapter.md（含附录A参数表/B证据对照/C缺口清单）、
  provenance_map.json、audit_report.json、build_report.json、章节预览、result.json
  （含 output_contract 全部字段、case_id、status、uncertainty、manual_confirmations、change_log、exceptions）。

## 评分维度对照

实际效果 40（七节强制覆盖+锚点可溯+引擎拦截）｜使用增益 25（解析装配秒级、先证据后行文）｜
创新增益 15（证据锚定双向溯源独有引擎 audit_provenance.py）｜可靠体验 10（Phase 0 骨架+异常表+partial 降级）｜
生态贡献 10（README/CHANGELOG/示例/规则模板可复用；GitHub: Austin071031/Academic-Writing-Skill）。

## 维护信息

- 版本 v2.0.0（2026-11-23）；基于 v1.0.0-证据锚定双向溯源 打包修复；变更见 CHANGELOG.md。
- 失败重查：`playground status --attempt-id <ID>`。
