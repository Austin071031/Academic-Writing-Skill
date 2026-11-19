# 最小调用示例（合成材料，标注为示例，非正式案例结果）

## 输入（合成）

同 v1.0.0 示例：`case.json`（demo-02）+ 合成 paper.pdf / config.yaml / train.log / train.py /
data_card.md。

## 关键差异：先登记矩阵

`work/element_matrix.json`（节选，示意）：

```json
{"params": {"train": {"eids": ["E0005", "E0006"], "section_anchor": "sections/03_params"},
            "val":   {"na": true, "reason": "早停用验证集，无独立超参"},
            "test":  {"na": true, "reason": "测试仅评测，不涉及超参"}}}
```

## 调用与示意输出

命令序列同 v1.0.0 示例，Phase 4 首步换为：

```bash
python3 /skills/weekly-skill/scripts/element_matrix.py --work /app/work --out /app/output
```

示意输出（示例）：

- `matrix_report.json`：`{"cells_total": 18, "missing_or_weak": [], "crossing_flags": [], "verdict": "pass"}`
- 若把"学习率 3e-4"误写进评测小节，crossing_flags 命中该句并要求改写——这是本版本的
  核心防护（示意行为，非正式案例结果）。
