# USAGE｜对照实验与统计口径

## 调用步骤

0. `init_result.py` → 1. `inspect_case.py` + `extract_evidence.py` → 2. 读 references/
（statistics_style_rules 等五件）→ 3. Agent 写 `experiment_matrix.json`、
`sections/01..07_*.md`、`table_rows.json`、`gaps.json`、`changes.json`、`status.json`、
`contract_extra.json` → 4. `exp_matrix.py` → `build_deliverables.py` →
`render_previews.py` → `validate_output.py --expect-status success`。命令逐字见 SKILL.md。

## 关键方法

- **矩阵先行**：每个实验变体/基线一行，正文比较句必须引用 R#。
- **闸门判定**：mixed dataset/split/metric、budget 不一致、缺统计口径、R# 未被引用都会被拦。
- **措辞三档**：表明/初步表明/有望，与证据强度绑定。

## 失败处理

- 闸门 fail：按 issues 逐条补登记或加 waiver；基线数值缺失进 gaps(high)。
- 材料只有图无数值：写"读图估计"标注或进 gaps，禁止脑补精确值。

## 自查方法

1. comparability_report verdict=pass；2. 每个比较句可映射到同口径行对；
3. 无编造统计；4. validate exit 0；5. 重跑一致。
