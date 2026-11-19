# 最小调用示例（合成材料，非正式案例结果）

## gap_chain.json（示意）

```json
{"gaps": [{"gid": "GAP1",
  "premises": [
    {"entry_ids": ["R002"], "limitation": "长时暴露下保护层开裂", "quote": "24 小时以上长时暴露下保护层出现裂纹"},
    {"entry_ids": ["R004"], "limitation": "未考察干空气工况", "quote": "200 次循环容量保持率 82%；未考察干空气工况"}],
  "gap_statement": "兼顾长时空气稳定性与产线兼容性的表面工程方案仍存在空白",
  "paper_response": "本文梯度缓冲层暴露 24 小时后界面电阻仅增加 12%",
  "response_evidence_loc": "P003"}]}
```

## 示意输出

`[gap_chain] 空白=1 有问题=0 verdict=pass`；
gap_derivation.md 渲染"前提（摘录）→缺口→本文对应（P003）"链条；
version_report.json 记录 per-gap 校验与 number_leaks（应为空）。
