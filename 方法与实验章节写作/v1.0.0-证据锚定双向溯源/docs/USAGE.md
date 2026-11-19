# USAGE｜证据锚定双向溯源

## 调用步骤

| 步骤 | 命令（绝对路径） | 产物 |
|-|-|-|
| 0 骨架 | `python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output` | result.json（running 骨架） |
| 1 侦查 | `python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work` | work/inspection.json + text/*.pages.txt |
| 1 抽取 | `python3 /skills/weekly-skill/scripts/extract_evidence.py --work /app/work` | work/evidence_candidates.jsonl、value_index.json |
| 2 规则 | 读 references/ 五个文件 | — |
| 3 写作 | Agent 写 work/sections/01..07_*.md、evidence_used.json、unused_evidence.json、table_rows.json、gaps.json、changes.json、status.json、contract_extra.json | — |
| 4 装配 | `python3 /skills/weekly-skill/scripts/build_deliverables.py --work /app/work --out /app/output` | 章节 + 附录 + result.json |
| 4 审计 | `python3 /skills/weekly-skill/scripts/audit_provenance.py --work /app/work --out /app/output` | audit_report.json（须 pass） |
| 4 预览 | `python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output` | 章节 PDF/TXT 预览 |
| 4 校验 | `python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work --expect-status success` | 闸门 PASS/FAIL |

## 关键方法

- **先证据后行文**：候选抽取只做"找"，采信由 Agent 回原文核对；quote 逐字。
- **双向闭合**：正向查泄漏（数字必须来自材料），反向查闲置（证据必须被用或说明）。
- **取舍留痕**：跨来源取值不同按 日志>配置>代码默认>论文正文 采信，changes.json 记录。
- **诚实降级**：缺口进附录C与 result.json，status 不夸大。

## 失败处理

- audit fail：读 audit_report.json 的 forward_leaks/backward_unused，逐条修正后重跑 Phase 4。
- validate fail：按 FAIL 信息修复（缺字段补 contract_extra.json；锚点缺失补采信）。
- PDF 不可解析：exceptions 记录，改用配置/日志/代码写作，uncertainty 注明。

## 自查方法

1. `audit_report.json verdict == pass`；2. `validate_output.py exit 0`；3. 附录B每条可点开
回到原文位置；4. result.json 无 `null` 状态的缺口；5. 重跑 Phase 4 输出一致（幂等）。
