# 完整标注示例（合成稿件，非正式案例结果）

> 全部内容为合成示意，非平台正式案例。

## 输入（合成摘录）

```markdown
## Results
Devices showed no significant degradation over 500 h [5]. These results suggest that
interface engineering may improve stability (Zhang et al., 2023). Only three compositions
were tested.
```

## 流程产物

1. `boundary_engine index`：
   - P006-s1：citations=[[5]]；hedges=[negation: no, suggestion: (无)]。
   - P006-s2：citations=[(Zhang et al., 2023)]；hedges=[suggestion: suggest, possibility: may]。
   - P006-s3：hedges=[limitation: only]。

2. Agent 译文（含故意错误）：

```jsonl
{"seg_id":"P006-s1","translation":"器件在500 h内性能稳定。"}
{"seg_id":"P006-s2","translation":"这些结果证明界面工程可以提升稳定性。"}
{"seg_id":"P006-s3","translation":"测试了三种组分。"}
```

3. `boundary_engine audit` 检出：
   - P006-s1：引用标记缺失 [5]（高）；否定范围丢失 no（高，“稳定”译丢了“未显著衰减”）。
   - P006-s2：引用标记缺失（高）；语气升格——suggest/may 被译为“证明/可以”（高）。
   - P006-s3：限定条件丢失 only（中）。

4. Agent 修订后复检清零；citation_fidelity 恢复 1.0。

## 示意输出（示例，非正式案例结果）

- boundary_audit.json：`{"summary":{"citations_total":2,"citations_preserved":2,"issues":0}}`（修订后）。
- audit_annotated.md：三句段 ⚠ 标注记录（修订前快照）。
