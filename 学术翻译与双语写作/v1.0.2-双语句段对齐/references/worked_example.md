# 完整标注示例（合成稿件，非正式案例结果）

> 全部内容为合成示意，非平台正式案例。

## 输入（合成摘录）

```markdown
## 2 Methods
We prepared the precursor solution at 1.4 M. The annealing temperature was 100 °C.
Figure 1. Schematic of the fabrication process.
[^1]: Supported by the NSF (Grant No. 52173200).
## References
[1] Kojima, A. et al. Organometal halide perovskites. JACS, 2009, 131: 6050-6051.
```

## 流程产物

1. `align_engine plan`：invariants = figures_tables["figure1"], footnotes["1"],
   formulas=0, references=1。
2. Agent 译文：

```jsonl
{"seg_id":"P005-s1","translation":"我们以1.4 M配制前驱体溶液。"}
{"seg_id":"P005-s2","translation":"退火温度为100 °C。"}
{"seg_id":"P006","translation":"图1. 制备过程示意图。"}
{"seg_id":"P007","translation":"[^1]: 受国家自然科学基金（项目号52173200）资助。"}
```

3. `align_engine audit`：
   - 全部句段 aligned；figures_tables 源 ["figure1"] ↔ 译 ["图1"] 数字归一一致；
     footnotes ["1"] 一致；references 1=1。
   - 若 P005-s2 漏译，则该句段 missing（高），bilingual.md 对应段显示【缺译】。
   - 若译文题注写成 "图2."，图表编号集合不一致（高）。

## 示意输出（示例，非正式案例结果）

- bilingual.md：〔P005·原文〕/〔P005·译文〕 成对，可直接逐段修改。
- alignment.json：`{"summary":{"aligned":4,"missing":0,"suspect":0}}`。
