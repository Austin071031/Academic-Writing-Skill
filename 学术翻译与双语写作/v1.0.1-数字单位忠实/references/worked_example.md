# 完整标注示例（合成稿件，非正式案例结果）

> 全部内容为说明流程的合成数据，非平台正式案例。

## 输入（合成摘录）

```markdown
## Results
The efficiency increased from 3.8% in 2009 to over 25% in 2023 [2-4].
Approximately 1.2 million articles were indexed. The uncertainty is ±0.3%.
```

## 流程产物

1. `number_engine ledger`（节选）：

```json
{"entries":[{"seg_id":"P006-s1","numbers":[
  {"raw":"3.8%","value":3.8,"unit":"%"},
  {"raw":"2009","value":2009,"unit":null},
  {"raw":"25%","value":25.0,"unit":"%"},
  {"raw":"2023","value":2023,"unit":null}]}]}
```

（[2-4] 为引用标记，内部数字已屏蔽，不入台账。）

2. Agent 译文（含故意错误）：

```jsonl
{"seg_id":"P006-s1","translation":"效率从2009年的3.8%提升至2023年的25%[2-4]。"}
{"seg_id":"P006-s2","translation":"约120万篇论文被收录。"}
{"seg_id":"P006-s3","translation":"不确定度为±0.3%。"}
```

3. `number_engine audit` 检出：
   - P006-s1：源 "over 25%" 译文 "25%"——值相等通过，但 over 属比较级语义，
     由边界类机制报“限定条件丢失”；数字引擎本身不报。
   - P006-s2：1.2 million ↔ 120万，归一等值，matched（不报）。
   - P006-s3：±0.3% 双侧一致，matched。
   若译文误作 "3.8%"→"3.8"（丢 %）：值相等但单位 null vs %，报“单位形式差异”（低）。
   若译文误作 "25%"→"25.0%"：值等、位异，同样报形式差异，Agent 复核改回。

## 示意输出（示例，非正式案例结果）

- number_audit.json：`{"summary":{"fidelity":1.0,"issues":0}}`（修订后）。
- result.json：`status="success"`，stats 含 coverage 与 protected_spans_total。
