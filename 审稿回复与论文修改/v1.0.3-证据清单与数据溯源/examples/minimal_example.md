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
1. 作者声称材料"性能较好"，但未与文献数据定量比较，请补充对比表，并且引用至少两篇近三年文献。
```

## 调用

按 SKILL.md 步骤 0–8：init_result → inspect_case → parse_manuscript → parse_comments → **Agent 复核 comments.json（needs_evidence/action_kind）** → 写 dispositions（R1-C1 两条子要求同引 EV1）与 edit_plan → **evidence_engine --stage demand** → Agent 终判 EV 状态后重跑 demand → revision_engine → 写回复信等 → **evidence_engine --stage provenance** → verify_revision → assemble_result → validate_output。

## 示意中间产物

evidence_checklist.json（demand 建档，示意）：

```json
[{"ev_id": "EV1", "sub_ids": ["R1-C1-s1", "R1-C1-s2"], "demand": "补文献",
  "status": "部分到位",
  "source": "baseline P005b（E3 落稿处）；证据本体材料外，待作者补充",
  "note": "已落稿但含【待补】占位……禁止编造文献条目或冒称已核验。"}]
```

注意 `sub_ids` 含两条子要求——"补对比表"与"补两篇文献"共享同一份文献证据，只建一条 EV。

## 示意输出（标明为示例）

```
[evidence_engine] demand: EV 条目=2 状态分布={'部分到位': 2}
[evidence_engine] provenance: 数字=17 溯源成功=12 意见给出=0 待补=3 未核实=2 evidence_map=3 新增人工确认=2
[verify] coverage/edit_claims/location/empty_talk/fabrication: PASS
[validate] PASS (status=success, outputs=8)
```

provenance_report.md 节选（示意）：

```
| 数字  | 出现位置                    | 基线/意见来源      | 判定   |
| 1450 | response_letter.md L12     | baseline P004 L17 | 溯源成功 |
| 5    | E1 new_text（…以 5 ℃/min…） | 基线与意见原文均未找到 | 未核实 |
| 50   | E1 new_text（…约 50 nm【待补…） | 【待补】占位（邻近标记） | 待补 |
```

未核实的 `5`（升温速率，基线与意见均未给出）自动写入 work/manual_confirmations.json，处置后重跑 provenance 至 exit=0 或留档交付。

> 以上数字与文本均为合成示例，用于说明接口与流程，不代表任何真实案例的评测结果。
