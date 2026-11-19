# 一致性规则（consistency_engine 的判定依据）

本文件是 `scripts/consistency_engine.py` 全部判定规则的文字版，供 Agent 复核对账结果时引用，也供人工审计复算。

## 1. 三方对账模型

返修交付存在三方"说法"，必须两两闭合：

```
   声称 (claims)                操作 (ops)                差异 (diff)
 回复信 E# 引用  ──────────→  edit_report applied ops ──→ 基线↔修订稿 diff regions
 dispositions 决策            （edit_plan 真实应用结果）    （唯一事实源）
```

- **差异是唯一事实源**：只有基线与 `revised_manuscript.md` 之间的真实差异能证明"改过了"；声称与操作都只是关于差异的陈述。
- 每条边的校验方向：
  - 声称→操作：回复信引用的 E# 必须存在且 status=applied（检查 D）；采纳/部分采纳的处置必须有 edit_ops 或 evidence（检查 C）。
  - 操作→差异：每个 applied op 的 new_text_head（前 30 字符、去全部空白后）必须是某个**非豁免 diff region 修订稿侧内容**的子串（检查 A）。注意这是**区域内部**强校验：文本出现在全稿未变区域不算数——那恰恰说明编辑没有生效。
  - 差异→操作：每个非豁免 diff region 必须被至少一个 op 认领（检查 B）。未被认领意味着"存在未声明的改动"，WARN 交人工确认。
- 判定结果两档：FAIL（退出码 1，阻断交付 success）与 WARN（退出码 0，但必须逐条人工确认并写入 manual_confirmations）。

## 2. diff region 判定

- 算法：`difflib.SequenceMatcher(autojunk=False)` 对基线与修订稿的**逐行去空白形式**做行级对齐，取 `get_opcodes()` 中 tag ≠ equal 的区段。
- region 字段：`id`（D1/D2…）、`tag`（replace/insert/delete）、基线侧行号区间、修订稿侧行号区间（1-based）、两侧内容头（首个非空行前 40 字符）、`claimed_by`。
- 行号显示约定：纯 insert 的基线侧无对应行，显示"（第 N 行后插入）"；纯 delete 的修订稿侧显示"（无对应行）"。

## 3. 噪音豁免规则

满足以下任一条件的 region 自动豁免（不参与认领核对，不计 WARN）：

1. region 两侧文本**去除全部空白字符后完全相等**（纯空行增删、缩进变化、行内空白差异）；
2. 由于对齐前先对每行做去空白归一化，绝大多数纯空白差异在 opcode 阶段即被合并为 equal，根本不会成为 region——豁免规则是双保险。

**不豁免**的情形（易被误认为噪音，实需人工确认）：段落顺序调换（多行 delete+insert 成对出现）、标题级别变化（`#` 数量改变）、标点全半角替换。这些会产生真实 region，未认领即 WARN。

## 4. 承诺句式词表与兑现判定

### 4.1 承诺句抽取

历史回复文件按句切分（。！？!?；; 与换行），句长 ≥8 字符且命中以下任一标记即抽取为承诺候选：

- 中文：`将`、`会`、`下一步`、`下一轮`、`后续`
- 英文（小写匹配）：`in the next`、`we will`

### 4.2 兑现判定（启发式，边界交人工）

- 对承诺句与本轮每条 disposition 的"response + 关联 op 的 new_text_head + rationale"分别取内容 bigram 集合（去标点、去停用词），计算重叠率 `score = |交集| / |承诺 bigram 数|`；
- 承诺句可提取 bigram 不足 3 个 → **无法判定**（WARN，列入 uncertainty）；
- 最佳匹配 score < 0.15 → **未兑现**（WARN，需在回复信说明）；
- score ≥ 0.4 且对应 op 无【待补】占位 → **已兑现**；
- score ≥ 0.4 但对应 op 含【待补】占位 → **部分兑现**（占位不算完整兑现）；
- 0.15 ≤ score < 0.4 → **部分兑现**（建议人工复核）。

台账条目字段：`promise_id / quote（承诺原文摘录）/ source_file / status / score / matched_sub_id / matched_op / note`。

## 5. 多轮文件命名约定

### 5.1 轮次来源

从 case.json 读取：`constraints.round` → `constraints.revision_round` → 顶层 `round` / `revision_round`，缺省 1。

### 5.2 历史文件嗅探

- 搜索范围：`--input-dir`（默认 `/input`）全目录递归，含 `materials/`；
- 文件名命中以下模式（不区分大小写）即候选：`response`、`reply`、`回复`、`rebuttal`、`round`、`r<数字>`；
- 排除：本轮自产文件（`response_letter.*` / `revised_manuscript.*` / `consistency_report.*` / `revision_ledger.*` / `edit_locations.*` / `evidence_checklist.*` / `result.*` / `verification.*` / `task.*`）与基线稿件本身；
- 推荐的上一轮回复信命名：`prev_response_round{N-1}.md`、`response_round1.md`、`回复信-第一轮.md`——含上述关键词即可被嗅探。

### 5.3 无历史文件的处理

- round = 1：台账记"第 1 轮，无历史承诺"，正常；
- round > 1：台账同样记无历史承诺，但追加 WARN"未嗅探到历史回复文件"——可能是文件缺失或命名不含关键词，提示人工确认，不静默放过。

## 6. 退出码约定

| 退出码 | 含义 | 处置 |
|-|-|-|
| 0 | 无 FAIL（可含 WARN） | WARN 逐条人工确认后可继续 |
| 1 | 存在 FAIL 项 | 逐项修复重跑；无法修复则降级 status 并在 uncertainty 说明 |
| 2 | 致命输入缺失（基线/修订稿不可读） | 先补齐前置步骤产物 |
