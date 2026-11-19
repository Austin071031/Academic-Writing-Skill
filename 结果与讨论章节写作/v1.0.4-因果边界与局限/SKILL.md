---
name: results-discussion-causal-limits
description: 结果与讨论章节写作的"因果边界与局限"方向技能。当任务要求区分相关、预测与因果表述、把机制推测明确标注为推测、并把研究局限写到方法/样本/测量/统计层面时使用。核心能力：相关-预测-因果三级措辞边界表、因果越界审计脚本（观察性语境中的因果动词检测）、机制推测标注规范、四层局限写作模板。适用于讨论段证据强度控制与局限性章节的实质化写作。
---

# 结果与讨论章节写作：因果边界与局限方向

## 1. 用途与适用条件

本 Skill 解决讨论段的两个系统性失败：**因果越界**（相关写成因果、单条件现象写成普遍机制、推测写成结论）与**局限空泛**（"本研究存在一些不足"——不写哪一层、不影响什么结论、如何改进）。

适用条件：输入材料为观察性/实验性科研数据（论文 PDF、图表、统计输出），需撰写结果与讨论章节。

核心原则：

1. **措辞跟着设计走**：判断材料支持的是相关、预测还是因果（判据见 `reference/causal_language.md`），措辞不得越级。
2. **机制推测必标注**：一切超出数据的机制解释写"我们推测……（推测，尚待验证）"。
3. **局限写到层**：每条局限必须落到方法、样本、测量、统计四层之一，并说明它对哪条结论构成何种威胁、如何改进。
4. **审计闭环**：交付前运行因果审计脚本，越界表述必须改写或降级。

## 2. 输入与输出

输入：`/input/case.json`（case_id、output_contract）、`/input/task.md`、`/input/` 科研材料。按扩展名识别文件，不凭标签假设内容。

输出（写入 `/app/output/`）：`result.json`（output_contract 全字段 + case_id + status + sources + uncertainty + change_log）、`results_and_discussion.md`、`causal_audit_report.json`、环境允许时 docx/PDF 预览。

## 3. 工作流程

### 步骤 1：读契约与材料

读 case.json/task.md 记录 output_contract 与语言；用 `reference/tool_recipes.md` 抽取材料。特别记录**研究设计信息**（随机分组？干预？纵向随访？纯观察？）到 `/app/work/design_notes.md`——这是因果定级的依据：设计信息在材料中找不到时，默认按"观察性"定级（最保守），并在 uncertainty 注明。

### 步骤 2：为关键论断做因果定级

对正文拟写的每个关键论断，在 `/app/work/design_notes.md` 中登记：

```
K1 X 与 Y 正相关（r = 0.71, p = 0.003, 图3A）→ 级A(相关)
K2 高剂量处理组 X 升高（随机分组干预实验, p = 0.002, 图1B）→ 级B(因果,限定该条件)
K3 X 通过 Y 通路起作用 → 级C(推测)
```

定级判据见 `reference/causal_language.md` 第 2 节。级 B 要求材料能支撑（随机化/干预/对照）；达不到一律级 A 或 C。

### 步骤 3：按边界表撰写结果段与讨论段

- 结果段：级 A 论断只写"相关/伴随/随……变化"；级 B 论断可写"使/导致"，但限定条件（剂量、体系、时间窗）；级 C 不出现在结果段。
- 讨论段：复述时保持原级；机制解释超出数据时一律"我们推测……（推测，尚待验证）"；与其他研究对照时，对方研究的因果强度也按同样标准转述（对方是相关性研究就不能写成"证明"）。
- 局限段按 `templates/limitations_block.md` 的四层模板成段，每条局限：层面 + 具体内容 + 威胁的结论 + 改进方向。

### 步骤 4：因果审计

```bash
python3 /skills/weekly-skill/scripts/check_causal.py \
  --text /app/output/results_and_discussion.md \
  --design /app/work/design_notes.md \
  --out /app/output/causal_audit_report.json
```

脚本检测（细则见 `reference/audit_rules.md`）：

1. 因果动词（导致、引起、造成、证明、决定、leads to、results in、demonstrates that、proves……）所在句：若 design_notes 中没有对应级 B 登记，且句内无"推测/可能/待验证"降级标记，则 fail；
2. 结果段出现机制推测词汇（机制、通路、mediates、mediation……）fail（应移讨论段并标注）；
3. 局限部分是否覆盖四层（方法/样本/测量/统计各至少一条，缺失层在报告中列出）——材料确实某层无局限时，在 uncertainty 说明后视为通过；
4. 每条局限是否含改进方向（"未来可……"句式）。

未通过项必须修改后重跑至 PASS。

### 步骤 5：交付

result.json（同前规范）、审计报告；环境允许时 docx/PDF；按 `checklists/final_checklist.md` 自查。

## 4. 异常处理

| 情况 | 处置 |
|-|-|
| 材料设计信息不足，无法判断随机化/干预 | 一律按观察性（级 A）处理；uncertainty 注明"材料未提供研究设计细节，因果表述按保守级别" |
| task.md 明确要求强结论（如基金式写作） | 仍以材料证据为措辞上限；强结论仅写为"有望/可能"，并在 uncertainty 说明措辞受限原因 |
| 局限确实写不满四层 | 只写有依据的层，缺省层在 uncertainty 说明"未发现该层明显局限"，不得编造 |
| 审计脚本误报（如引用他人文献中的因果表述） | 给该句加引文锚并确认系转述；仍在 uncertainty 记录误报条目 |

## 5. 最小调用示例（示意，非真实案例答案）

输入（示意）：`/input/case.json` 含 `{"case_id":"demo-05","output_contract":["section_md","language"]}`；材料为观察性队列论文（X 与 Y 相关，r = 0.71，p = 0.003，图3A；无干预实验）。

调用：抽取材料→design_notes 定级（K1 级 A、K3 级 C）→按边界表写正文与四层局限→check_causal.py PASS→交付。

示意输出（节选）：

```json
{
  "case_id": "demo-05",
  "section_md": "……X 与 Y 呈正相关（r = 0.71，p = 0.003，图3A）……我们推测 X 可能通过 Y 通路起作用（推测，尚待验证）……本研究的局限：样本层面，单中心队列（n = 128）限制外推性；测量层面，X 仅基线单次测量，无法刻画暴露变化；统计层面，未校正混杂因素 Z……",
  "language": "zh",
  "status": "success",
  "sources": {"design_notes": "design_notes.md（工作底稿）", "audit": "causal_audit_report.json"},
  "uncertainty": ["材料未提供研究设计细节，按观察性级别表述"],
  "change_log": ["初稿写'X 导致 Y 升高'，因无干预设计降级为相关表述"]
}
```

## 6. 资源清单

- `scripts/check_causal.py`：因果越界与局限完整性审计脚本（stdlib）。
- `reference/causal_language.md`：相关-预测-因果三级措辞边界表与判据。
- `reference/audit_rules.md`：审计脚本判定细则。
- `templates/limitations_block.md`：四层局限写作模板。
- `reference/tool_recipes.md`：材料抽取命令清单。
- `checklists/final_checklist.md`：交付前自查清单。
