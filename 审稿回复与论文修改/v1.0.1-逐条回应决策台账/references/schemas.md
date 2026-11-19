# 数据契约（JSON Schema 说明）

所有 JSON 用 UTF-8、无 BOM。Agent 手写的文件必须先能被 `python3 -m json.tool` 解析再进入管线。

## work/dispositions.json（Agent 手写，每子要求一条）

```json
[{
  "sub_id": "R1-C1-s1",
  "comment_id": "R1-C1",
  "decision": "采纳 | 部分采纳 | 不采纳",
  "response": "回复要点（≥20字，必须含 E#/EV#/P###/理由词 之一）",
  "edit_ops": ["E1"],
  "evidence": ["EV1"],
  "tone": "接受 | 澄清 | 礼貌反驳 | 申诉"
}]
```

规则：
- 采纳/部分采纳 且声称改了正文 → `edit_ops` 非空且指向 edit_plan 中存在的 op_id；
- 不采纳 → `response` 必须给出学术理由（引基线原文锚点或文献），tone 取 澄清/礼貌反驳；
- 需要证据但未到位 → `evidence` 引用证据清单条目且 response 说明状态。

## work/edit_plan.json（Agent 手写）

```json
[{
  "op_id": "E1",
  "comment_ref": "R1-C1-s1",
  "action": "replace | insert_after | insert_before | delete | replace_paragraph | append_section",
  "para_id": "P005",
  "section": "讨论",
  "anchor_quote": "从 structure.json 段落原文逐字复制的片段（≥10字）",
  "new_text": "替换或插入的文本，可含【待补：说明】占位",
  "rationale": "为什么这样改"
}]
```

规则：
- `anchor_quote` 必须逐字复制，禁止凭记忆改写；insert_* 的锚点是被插入位置的邻段；
- `delete` 只接受精确命中；整段删除用 replace_paragraph 配空 new_text；
- 一个 op 只做一件事；同一子要求的多处修改拆成多个 op；
- 新数据/新文献/新实验结果一律用【待补：…】占位，禁止编造。

## work/evidence_map.json

```json
[{"claim": "回复或修订稿中的关键论断", "source": "baseline P012 / comments R1-C2 / EV1", "kind": "baseline|comment|evidence|placeholder"}]
```

## work/change_log.json

```json
[{"op": "E1", "comment_ref": "R2-C1-s1", "desc": "补充升温速率", "file": "revised_manuscript.md"}]
```

## work/uncertainty.json / manual_confirmations.json / exceptions.json / stats.json

- uncertainty：字符串列表，写明不确定内容与原因；
- manual_confirmations：字符串列表，需作者人工确认项（占位数值、冲突取舍）；
- exceptions：字符串列表，运行异常与处置；
- stats：`{"n_comments":…,"n_subs":…,"n_ops_applied":…,"n_placeholders":…}`。

## work/evidence_checklist.json（可选，供 V4 类流程与 assemble 使用）

```json
[{"ev_id": "EV1", "sub_id": "R1-C1-s1", "demand": "补实验|补数据|补文献|重做分析",
  "status": "到位|部分到位|无法补做", "source": "baseline P012 或 待补说明", "note": "替代说明"}]
```
