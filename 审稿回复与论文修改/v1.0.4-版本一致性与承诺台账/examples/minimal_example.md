# 最小调用示例（合成数据，仅为接口示意，非正式案例结果）

## 输入（示意）

`case.json`：`{"case_id":"demo-02","constraints":{"round":2},"output_contract":["revised_manuscript","response_letter","edit_locations","evidence_checklist"]}`

`materials/manuscript-baseline.md`（节选，合成）：

```
## 讨论
容量衰减主要源于硅颗粒的粉化。与其他体系相比，本材料性能较好。
```

`materials/reviewer-comments.md`（节选，合成）：

```
## Reviewer 1
1. 请补充与已发表工作的定量对比。
```

`materials/prev_response_round1.md`（上一轮回复信，合成）：

```
关于对比数据，我们将在下一轮补充对比表，并完善统计说明。
```

## 调用

按 SKILL.md 步骤 0–8：init_result → inspect_case → parse_manuscript（+ 嗅探到 1 个历史回复文件）→ parse_comments → 复核 → 写 dispositions/edit_plan → revision_engine → 写回复信等 → **consistency_engine** → verify_revision → assemble_result → validate_output。

## 示意中间产物

edit_plan.json（节选，示意）：

```json
[{"op_id":"E3","comment_ref":"R1-C1-s1","action":"insert_after",
  "anchor_quote":"与其他体系相比，本材料性能较好。",
  "new_text":"表 1 汇总了本工作与已报道硅碳负极的容量保持率对比【待补：近三年两篇文献数据】。",
  "rationale":"补充文献定量对比（数据待补，如实标注）"}]
```

## 示意输出（标明为示例）

```
[consistency] diff 区域=3（豁免 0） applied_op=5 落点=5 未认领区域=0
[consistency] 承诺台账：round=2 历史文件=1 承诺=1（已兑现=0 部分兑现=1 未兑现=0 无法判定=0）
[consistency] overall=PASS
[verify] coverage/edit_claims/location/empty_talk/fabrication: PASS
[validate] PASS (status=success, outputs=9)
```

revision_ledger.json（节选，示意）：

```json
{"round": 2,
 "promises": [{"promise_id": "PR1",
   "quote": "关于对比数据，我们将在下一轮补充对比表，并完善统计说明。",
   "source_file": ".../materials/prev_response_round1.md",
   "status": "部分兑现", "matched_sub_id": "R1-C1-s1", "matched_op": "E3",
   "note": "内容对应但以【待补】占位落实"}]}
```

consistency_report.md 三方对账（节选，示意）：

```
| D3 | insert | （第 21 行后插入） | 22-25 | 表 1 汇总了本工作…对比【待补：近… | E2, E3 |
| E3 | D3 | ✅ 落在差异区域内 |
```

> 以上数字与文本均为合成示例，用于说明接口与流程，不代表任何真实案例的评测结果。
