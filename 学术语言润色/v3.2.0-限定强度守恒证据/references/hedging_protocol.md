# 限定强度守恒协议（hedging protocol）

## 三档词表（判定依据）

| 档 | 中文 | 英文 |
|-|-|-|
| 强（0） | 证明、证实、确证、必然、肯定、毫无疑问、首次证明 | prove, confirm, definitively, establish, always, must, undoubtedly |
| 中（1） | 表明、显示、说明、揭示、反映出、显著（统计义）、一致表明 | suggest, indicate, show, demonstrate, reveal, support, consistent with |
| 弱（2） | 可能、或许、有望、提示、倾向于、初步、约、大致、一定程度上 | may, might, could, possibly, potentially, likely, appear, seem, tend, preliminary, approximately, roughly, partially |

规则：不得跨档替换；不得静默删除限定词；同档替换（may→might）允许，理由注明"同档替换"。
因果（导致/引起/cause/lead to/due to）与相关（相关/伴随/correlate/consistent with）不可互换。
否定词（不/未/无/并非/not/no/never/without）与量词（所有/部分/some/all）增删即改命题。

## 修改卡的强度标注（本版新增，必填）

每张 modify 卡在 types/reason 之外加两行：

```markdown
- 强度标注：限定词 中档（表明）→ 中档（表明）｜数值 [15%]→[15%]｜引用 [1]→[1]｜
  图表 图2→图2｜否定 无→无｜因果 相关→相关
```

`→` 前后照抄原文与改文的对应要素；要素不存在写"无"。**任何一格不一致必须能解释**：
要么是笔误（立即改回），要么是 intentional change（理由写明依据并列入人工确认）。

## 守恒证据表（conservation_evidence.md，随稿交付）

```markdown
| 句 ID | 限定词 | 数值/单位 | 引用 | 图表指向 | 否定 | 因果 | 结论 |
|---|---|---|---|---|---|---|---|
| B3-S2 | 中档→中档 | 15%→15% | [1]→[1] | 无→无 | 无→无 | 相关→相关 | ✓ 守恒 |
| B5-S1 | 强档→中档 | — | — | — | — | — | ⚠ 降档，见人工确认#3 |
```

- 每句 modify 一行；keep 句汇总一行"未改动，守恒"。
- 表尾写签署行：**"回读签署：以上 N 句 modify 已逐句回读，守恒 N-? 句，例外 ? 句均已列入人工确认。"**

## 回读签署（第 4 步交付前必做）

通读改后全文，逐句核对强度标注与守恒证据表；签署行写在表尾与 result.json 的
change_records.conservation 字段：
`{"modified": N, "conserved": N-x, "exceptions": [{"id": "…", "reason": "…"}]}`。
