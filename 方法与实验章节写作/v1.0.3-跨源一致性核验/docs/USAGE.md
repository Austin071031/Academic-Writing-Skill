# USAGE｜跨源一致性核验

## 调用步骤

0. `init_result.py` → 1. `inspect_case.py` + `extract_evidence.py` +
`cross_source_check.py --phase detect` → 2. 读 references/（consistency_rules 等五件）→
3. Agent 写 `conflict_resolutions.json`、`sections/01..07_*.md`、`table_rows.json`、
`gaps.json`、`changes.json`、`status.json`、`contract_extra.json` → 4.
`cross_source_check.py --phase verify` → `build_deliverables.py` → `render_previews.py` →
`validate_output.py --expect-status success`。命令逐字见 SKILL.md。

## 关键方法

- **机检候选 + 人工裁决**：引擎只报"同参数名跨源多值"，采信由 Agent 按三级优先级定。
- **数值归一化**：科学计数与小数同组，避免等价误判。
- **裁决闭环**：verify 阶段强制每个候选冲突有裁决或升级，杜绝静默删冲突。

## 失败处理

- verify fail（unresolved 非空）：回 Phase 3 补写裁决。
- 检测误报（同名不同含义）：在 rationale 说明后 escalated 或按豁免情形关闭。
- 材料单源无机检冲突：正常装配，report 记 0。

## 自查方法

1. consistency_report verdict=pass；2. 正文取值都能在 resolutions 找到 chosen_value；
3. changes.json 条数 ≥ 裁决条数；4. validate exit 0；5. 重跑 Phase 4 一致。
