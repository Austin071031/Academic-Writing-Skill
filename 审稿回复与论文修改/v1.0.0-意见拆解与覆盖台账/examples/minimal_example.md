# 最小调用示例（合成数据，仅为接口示意，非正式案例结果）

## 输入（示意）

`case.json`：`{"case_id":"demo-01","output_contract":["revised_manuscript","response_letter","edit_locations","evidence_checklist"]}`

`materials/manuscript-baseline.md`（节选，合成）：

```
## 结果
复合材料首次放电比容量为 1450 mAh/g，首次库仑效率为 78%。循环 100 次后容量保持率为 85%。
```

`materials/reviewer-comments.md`（节选，合成）：

```
## Reviewer 2
1. 实验方法中缺少碳化升温速率和硅粉粒径等关键参数，必须补充。
```

## 调用

按 SKILL.md 步骤 0–8：init_result → inspect_case → parse_manuscript → parse_comments → decompose(first) → 复核 → 写 dispositions/edit_plan → revision_engine → 写回复信等 → decompose(audit) → verify_revision → assemble_result → validate_output。

## 示意中间产物

edit_plan.json（节选，示意）：

```json
[{"op_id":"E1","comment_ref":"R2-C1-s1","action":"replace",
  "anchor_quote":"在氩气保护下 800 ℃ 碳化 2 h",
  "new_text":"在氩气保护下以 5 ℃/min 升温至 800 ℃ 碳化 2 h（硅粉粒径【待补：供应商规格书】）",
  "rationale":"补充关键实验参数"}]
```

## 示意输出（标明为示例）

```
[decompose] stage=audit 子要求=7 已覆盖=7 重叠=0 冲突=0 证据依赖=0
[verify] coverage/edit_claims/location/empty_talk/fabrication: PASS
[validate] PASS (status=success, outputs=7)
```

result.json（节选，示意）：`{"case_id":"demo-01","status":"success","verification_overall":true, ...}`

> 以上数字与文本均为合成示例，用于说明接口与流程，不代表任何真实案例的评测结果。
