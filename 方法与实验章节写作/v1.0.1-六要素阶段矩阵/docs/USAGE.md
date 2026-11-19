# USAGE｜六要素阶段矩阵

## 调用步骤

0. `init_result.py`（骨架）→ 1. `inspect_case.py` + `extract_evidence.py`（侦查+候选）→
2. 读 references/（condition_matrix_rules 等五件）→ 3. Agent 写 `element_matrix.json`、
`sections/01..07_*.md`、`table_rows.json`（scope 必填）、`gaps.json`、`changes.json`、
`status.json`、`contract_extra.json` → 4. `element_matrix.py` → `build_deliverables.py` →
`render_previews.py` → `validate_output.py --expect-status success`。

完整命令行见 SKILL.md（绝对路径，逐字可复制）。

## 关键方法

- **先矩阵后段落**：18 格先登记证据归属，行文只是把格子翻译成阶段分明的段落。
- **na 也要理由**：材料不覆盖的格子显式说明原因，防止静默缺项。
- **串台检测**：评测/测试小节出现训练超参赋值句即 flag；同预算对照是合法例外但须写明。
- **幂等**：全部 engine 纯函数式读 work 写 report，可反复重跑。

## 失败处理

- matrix fail（缺格/na 无理由）：回 Phase 3 补登记；材料确实没有的改 na+理由并进 gaps。
- 串台 flag：改写对应段落，把训练条件移回第二节训练段。
- validate fail：按 FAIL 信息补 contract_extra 或修复 outputs 指向。

## 自查方法

1. matrix_report verdict=pass；2. validate exit 0；3. 附录A每行 scope 可判定阶段；
4. 正文各段首句阶段归属清晰；5. 重跑 Phase 4 输出一致。
