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
## Reviewer 1
1. 作者声称材料"性能较好"，但未与文献数据进行定量比较，请补充对比表，并且引用至少两篇近三年文献。
```

## 调用

按 SKILL.md 步骤 0–8：init_result → inspect_case → parse_manuscript → parse_comments → 复核 → 写 dispositions/edit_plan/evidence_checklist → revision_engine → **response_engine generate → 润色 → response_engine audit** → verify_revision → assemble_result → validate_output。

## 示意中间产物

dispositions.json（节选，示意）：

```json
[{"sub_id":"R1-C1-s1","comment_id":"R1-C1","decision":"部分采纳",
  "response":"已在讨论段插入对比表占位（E3），因基线未含文献数据，所需数据列入证据清单 EV1，到位后填入。",
  "edit_ops":["E3"],"evidence":["EV1"],"tone":"接受"}]
```

## 示意输出（标明为示例）

generate 产出的回复信条目（节选，示意）：

```
- **R1-C1-s1**（决策：部分采纳｜语气：接受）
  - 回应：已在讨论段插入对比表占位（E3），因基线未含文献数据，所需数据列入证据清单 EV1，到位后填入。
  - 修改指涉：E3（applied，修订稿第 23 行，含【待补】占位）
  - 证据指涉：EV1（近三年两篇文献数据｜无法补做）
```

audit 检出能力演示（示意）：把上条 response 改成"感谢审稿人的建议，我们已认真考虑。"后重跑 audit——

```
[audit] off_topic: FAIL
  [答非所问] R1-C1-s1（add_citation）：action_kind=add_citation 要求证据支撑，回应须引用 EV# 或写明 待补/无法/补做
[audit] overall=FAIL   （exit=1）
```

修复 response 并重跑后：

```
[generate] 审稿人=2 意见=5 子要求=7 op=5 问题=0
[audit] off_topic/tone_consistency/tone_redlines/letter_structure: PASS
[verify] overall=PASS
[validate] PASS (status=success, outputs=7)
```

result.json（节选，示意）：`{"case_id":"demo-01","status":"success","skill":"revision-point-by-point-response v1.0.1","verification_overall":true, ...}`

> 以上数字与文本均为合成示例，用于说明接口与流程，不代表任何真实案例的评测结果。
