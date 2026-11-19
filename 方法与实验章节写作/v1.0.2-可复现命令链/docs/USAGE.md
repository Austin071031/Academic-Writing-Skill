# USAGE｜可复现命令链

## 调用步骤

0. `init_result.py` → 1. `inspect_case.py` + `extract_evidence.py` → 2. 读 references/
（reproduction_checklist_rules 等五件）→ 3. Agent 写 `repro_checklist.json`、
`sections/01..07_*.md`、`table_rows.json`、`gaps.json`、`changes.json`、`status.json`、
`contract_extra.json` → 4. `repro_gate.py` → `build_deliverables.py` → `render_previews.py`
→ `validate_output.py --expect-status success`。命令逐字见 SKILL.md。

## 关键方法

- **七项闸门**：缺项 fail；材料没有就进 gaps 降级，不静默。
- **命令入章**：清单中的命令首令牌必须在第六节正文出现。
- **数据获取三选一**：URL/校验和/路径，复现者必须能拿到同一份数据。
- **开销推算留痕**：est_cost 的推算式写进 changes.json。

## 失败处理

- repro_gate fail：按 repro_report.missing 补登记；命令未入章就改第六节。
- 材料无版本/命令：按规则重构或追问，禁止编造版本号。

## 自查方法

1. repro_report verdict=pass；2. validate exit 0；3. 第六节命令可复制执行；
4. 第七节每条限制含具体场景；5. 重跑 Phase 4 输出一致。
