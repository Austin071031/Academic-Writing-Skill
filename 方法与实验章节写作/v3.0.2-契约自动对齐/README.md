# methods-reproduction-gate v3.0.2｜可复现命令链 + 契约自动对齐

复现七要素（代码版本/环境/硬件/数据获取/命令/种子/开销）闸门 + 命令必须写进正文校验。

## 与父辈（v2.0.2，62.6667）的唯一差异

契约自动对齐：init_result 自动推导 contract_extra 草稿；新增 contract_audit.py（task.md 原子指令拆解+装配后契约/指令覆盖校验）。

**提分依据**：父辈的 contract_extra.json 全靠 Agent 手写，字段映射错即 validate fail→partial；且章节结构不服从 task.md 指令。
**改动文件**：init_result.py、build_deliverables.py 加草稿合并；新增 scripts/contract_audit.py；SKILL.md 加 Phase 1.5 与 Phase 4 校验步。其余与父辈完全一致（打包形态、脚本、规则、契约）。


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
  provenance_map.json、repro_report.json、build_report.json、章节预览、result.json
  （含 output_contract 全部字段、case_id、status、uncertainty、manual_confirmations、change_log、exceptions）。

## 评分维度对照

实际效果 40（七节强制覆盖+锚点可溯+引擎拦截）｜使用增益 25（解析装配秒级、先证据后行文）｜
创新增益 15（可复现命令链独有引擎 repro_gate.py）｜可靠体验 10（Phase 0 骨架+异常表+partial 降级）｜
生态贡献 10（README/CHANGELOG/示例/规则模板可复用；GitHub: Austin071031/Academic-Writing-Skill）。

## 维护信息

- 版本 v3.0.2（2026-11-25）；基于 v1.0.2-可复现命令链 打包修复；变更见 CHANGELOG.md。
- 失败重查：`playground status --attempt-id <ID>`。
