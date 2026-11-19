# 最小调用示例（合成示例，仅示意接口与流程，非正式案例结果）

hedging_report.json（节选）
```json
{"items":[
 {"location":"draft.md §2 第3句","trigger":"导致","certainty":"可能",
  "original":"高盐饮食导致高血压。","revised":"高盐饮食与血压升高相关，在队列研究中呈剂量反应关系。",
  "rationale":"证据为观察性相关，因果动词越级"},
 {"location":"draft.md §4 第1句","trigger":"唯一","certainty":"很可能",
  "original":"该方案是唯一有效的干预。","revised":"在所给文献范围内，该方案是报告有效的干预之一。",
  "rationale":"材料仅覆盖部分文献，全称断言越出证据范围"},
 {"location":"draft.md §5","trigger":"conflict","certainty":"可能",
  "original":"（初稿仅写阳性结果）","revised":"两项研究报告终点改善，一项未达显著；分歧可能与样本量有关。",
  "rationale":"冲突证据并陈，各自限定"}
]}
```
