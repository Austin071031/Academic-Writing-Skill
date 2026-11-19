# 最小调用示例（合成材料，非正式案例结果）

## contributions.json（示意）

```json
{"items": [
  {"cid": "CT1", "statement": "提出湿化学梯度缓冲层方法，在 8 nm 尺度实现成分梯度可控",
   "type": "method", "evidence_locs": ["P007"], "scope_words": []},
  {"cid": "CT2", "statement": "暴露 24 小时后界面电阻仅增加 12%",
   "type": "experiment", "evidence_locs": ["P003"], "scope_words": []},
  {"cid": "CT3", "statement": "本文首次实现全面稳定性提升",
   "type": "conclusion", "evidence_locs": ["P011"], "scope_words": ["首次", "全面"]}
]}
```

## 示意输出

CT1/CT2 核验通过；CT3 因 P011 无比较性数据被标记 overclaim_risk 并写入
manual_confirmations；`[contrib] 贡献=3 有问题=1 范围词=2 verdict=warn`；
contributions_check.md 逐行给出结论列。
