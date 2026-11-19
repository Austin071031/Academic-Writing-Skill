# 最小调用示例（合成材料，非正式案例结果）

## ref_classification.jsonl（示意，3 行）

```json
{"entry_id": "R001", "role": "foundation", "rationale": "分解机理奠基综述，确立问题与研究脉络"}
{"entry_id": "R002", "role": "key", "rationale": "均质包覆代表，直接支撑空白推导"}
{"entry_id": "R006", "role": "recent", "rationale": "2024 年工艺窗口定量工作"}
```

## 示意输出

`[coverage] 库=7 被引=7 未覆盖关键=0 裸论断=0 近期=4/4 verdict=pass`；
coverage_report.md 列出分类完整性、双向绑定、近期覆盖与元数据缺失四节；
result.json 的 manual_confirmations 为空；validate_output PASS（正文-文献表一致）。
