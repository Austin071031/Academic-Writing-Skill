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

按 SKILL.md 步骤 0–8：init_result → inspect_case → parse_manuscript → parse_comments → 复核 → 写 dispositions/edit_plan → revision_engine → **anchor_engine（首跑：生成 location_table.md）** → 按 anchor_rules 写信 → **anchor_engine（复跑：核验定位声明）** → verify_revision → assemble_result → validate_output。

## 示意中间产物

edit_plan.json（节选，示意）：

```json
[{"op_id":"E1","comment_ref":"R2-C1-s1","action":"replace",
  "anchor_quote":"在氩气保护下 800 ℃ 碳化 2 h",
  "new_text":"在氩气保护下以 5 ℃/min 升温至 800 ℃ 碳化 2 h（硅粉粒径【待补：供应商规格书】）",
  "rationale":"补充关键实验参数"}]
```

回复信中的定位声明（示意）：

```
已补充升温速率，方法段（P003）现为“在氩气保护下以 5 ℃/min 升温至 800 ℃ 碳化 2 h”（E1）。
```

该引文逐字存在于修订稿，E1 在 applied 集合内，P003 在 structure 中——三项核验均可通过。

## 示意输出（标明为示例）

```
[revision_engine] 应用=5 失败=0 占位=3 → revised_manuscript.md (724 chars)
[anchor_engine] 双坐标 5 处；变更区域 3 个；模糊锚预警 0 处；回复信核验=已执行；不可核对声明 0 处
[verify] coverage/edit_claims/location/empty_talk/fabrication: PASS
[validate] PASS (status=success, outputs=6)
```

检出能力演示（合成，标明为演示）：向信中注入一句修订稿不存在的引文 `"本材料在千次循环后容量保持率仍为 98% 以上"`，复跑引擎输出：

```
[anchor_engine][FAIL] 引文未找到 第32行: 引文既不在 revised_manuscript.md 也不在意见原文中
[anchor_engine] ... 不可核对声明 1 处        → exit 1
```

移除该句后 exit=0。同理可检出悬空 E 引用（E引用悬空）与旧稿行号（行号越界）。

result.json（节选，示意）：`{"case_id":"demo-01","status":"success","verification_overall":true, ...}`

> 以上数字与文本均为合成示例，用于说明接口与流程，不代表任何真实案例的评测结果。
