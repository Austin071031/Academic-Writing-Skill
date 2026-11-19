---
name: academic-writing-revision-tracking
description: 学术写作客户端·修订追踪方向。当任务要求对学术稿件（DOCX/章节稿）按工作单定点修改、保留可逐条接受或拒绝的修订记录、导出可编辑文档与预览时使用。覆盖“接收稿件—指令锚定—修订落地—逐条台账—双变体导出—保真核验—结构化结果”全闭环。
---

# 学术写作客户端 · 修订追踪（v1）

## 用途

把组织方给出的修改指令（task.md / organizer-edit-workorder.json）落到稿件的具体句子或段落上，
以 DOCX **原生修订标记**（`w:ins` / `w:del`）落地，生成可逐条接受或拒绝的改动台账
（changes.json），并交付：修订稿、接受稿、拒绝稿（应与原稿一致）三个可编辑 DOCX
及 PDF/PNG 预览。任何改动都有可定位的原位置、改后内容、依据和状态。

适用条件：输入为学术稿件（DOCX 优先；Markdown/纯文本走降级路径）加明确的修改指令；
不需要联网；全部脚本为 Python 3 标准库实现，无 pip 依赖。

## 调用方式

本 Skill 被加载后，按下方“执行流程”逐步操作。脚本位于本 Skill 目录的 `scripts/` 下，
运行时目录约定为 `/skills/weekly-skill`；先用以下方式确定脚本目录，勿硬编码猜测：

```bash
SKILL_DIR="${SKILL_DIR:-/skills/weekly-skill}"
ls "${SKILL_DIR}/scripts"   # 确认存在后再调用
```

所有脚本只依赖 Python 3.8+ 标准库。DOCX 渲染预览需要 LibreOffice（`soffice`），
不可用时如实降级并在结果中注明。

## 执行流程

### 阶段 0：读取事实与契约（必须先做，不得跳过）

1. 通读 `/input/case.json`、`/input/task.md`、`/input/organizer-edit-workorder.json`
   （若存在）。**以实际文件内容为准，不得依据题目标签推断材料内容。**
2. 从 `case.json` 原样提取 `case_id` 与 `output_contract` 的全部字段名；
   这些是 result.json 必须出现的键。
3. 清点 `/input/` 下所有文件（含子目录），登记每个文件的路径、类型、大小；
   识别主稿件（DOCX/Markdown/TEX/PDF）。PDF 稿件先用 pdftotext 抽文本判断
   是否扫描件（抽取文本 < 400 字符按扫描件处置：能 OCR 则 OCR 并注明，不能则
   如实标 partial，绝不把空内容当作成功）。
4. **立即**用 result_builder 落盘一版部分结果，之后每完成一个阶段更新一次：

```bash
python3 "${SKILL_DIR}/scripts/result_builder.py" /input/case.json /app/output/result.json \
  --status partial --set 'uncertainty=["稿件格式待确认"]'
```

### 阶段 1：保全原稿与结构摸底

```bash
mkdir -p /app/work/originals /app/work/stage
cp -a /input/. /app/work/originals/          # 原稿只读保全
python3 "${SKILL_DIR}/scripts/docxkit.py" inspect /app/work/originals/<主稿件>.docx \
  > /app/work/stage/manifest.json             # 段落数/表格/图片/公式/脚注/域清单
python3 "${SKILL_DIR}/scripts/docxkit.py" dump  /app/work/originals/<主稿件>.docx \
  > /app/work/stage/paras.json                # 全文段落快照（锚定与差分的基础）
```

原稿目录 `/app/work/originals` 从此不再写入。

### 阶段 2：指令锚定（改得准的前提）

```bash
python3 "${SKILL_DIR}/scripts/workorder.py" /input /app/work/stage/paras.json \
  /app/work/stage/edit_plan.json
```

逐条核对 edit_plan：每条指令应落到具体段落（`anchor_method` 为
exact/heading/keyword）。**`none` 或 `keyword-weak` 的条目不得猜着改**：
回到 task.md 与稿件重新定位；仍无法唯一定位的，记入 `human_confirmations`，
该条状态标 `skipped-needs-confirmation`，不得擅自扩大改动范围。
术语统一类指令（含“统一”“全部”）按全量出现处处理，并在台账中记录每处出现。

### 阶段 3：形成修改明细并应用修订

对每条指令，先写出修改明细 `edit_details.json`（Agent 的语义判断集中在这里，
脚本负责机械落地）：

```json
{
  "E1": {"type": "replace", "old": "弹性模量", "new": "杨氏模量",
         "basis": "指令要求的术语统一；仅措辞层面，事实不变"},
  "E2": {"type": "delete", "old": "然而，现有方法存在精度不足的问题[2]。",
         "basis": "指令明确要求删除该句"},
  "E3": {"type": "insert_after", "anchor_text": "……测定模量",
         "new": "新增句……", "basis": "新增内容仅来自材料内事实，未引入外部数据"},
  "E4": {"type": "note", "basis": "数字核对：两处一致，无需改写"}
}
```

纪律（对应“AI 修改”要求的可控性）：
- `old` 必须是原稿中逐字存在的片段；不得凭印象改写。
- `new` 不得引入材料之外的事实、数字或引用；新增论断必须在 `basis` 中说明来源。
- 禁止整段重写：一处改动的字符占比超过该段一半且指令未明确授权时，拆成多条
  小改动或标人工确认。

应用修订（生成修订稿 + 台账 + 接受/拒绝两个变体）：

```bash
python3 "${SKILL_DIR}/scripts/revisions_apply.py" \
  /app/work/originals/<主稿件>.docx /app/work/stage/edit_plan.json /app/work/stage \
  --edits-json /app/work/stage/edit_details.json
```

产出：`revised_tracked.docx`（含原生修订）、`changes.json`（逐条台账）、
`accepted.docx`、`rejected.docx`。

### 阶段 4：保真核验（格式不塌）

```bash
printf '%s\n' '<术语统一的原词>' '<删除句关键词>' > /app/work/stage/whitelist.txt
python3 "${SKILL_DIR}/scripts/audit_diff.py" /app/work/originals/<主稿件>.docx \
  /app/work/stage/accepted.docx /app/work/stage/whitelist.txt \
  > /app/work/stage/fidelity.json
```

检查 `fidelity_breaks`：表格/图片/公式/脚注/超链接/分节数量必须前后一致；
不一致时先修复再交付，修复不了就如实写入 uncertainty。
另用 `docxkit.py revisions revised_tracked.docx` 复核修订数与台账一致。

### 阶段 5：导出预览与交付物归档

```bash
python3 "${SKILL_DIR}/scripts/render_preview.py" /app/work/stage/revised_tracked.docx \
  /app/output/previews 3
cp /app/work/stage/revised_tracked.docx /app/output/revised_document.docx
cp /app/work/stage/changes.json        /app/output/change_log.json
cp /app/work/stage/fidelity.json       /app/output/fidelity_report.json
```

渲染不可用时保留 DOCX 交付并在 result.json 中注明降级原因。

### 阶段 6：结构化结果（诚实契约）

```bash
python3 "${SKILL_DIR}/scripts/result_builder.py" /input/case.json /app/output/result.json \
  --status success \
  --set 'revised_document=/app/output/revised_document.docx' \
  --set 'change_log=/app/output/change_log.json' \
  --set 'previews=["/app/output/previews/revised_document.pdf"]' \
  --set 'uncertainty=[]' --set 'human_confirmations=[]'
```

- `status` 取值如实：`success`（全部指令完成且核验通过）、`partial`（存在跳过/
  降级/未确认项）、`failed`（无法完成）。有缺口宁可 partial 不虚报 success。
- `output_contract` 的每个字段都必须出现在 result.json；脚本会把缺失键列入
  `missing_fields` 并先填 null——提交前确认 `missing_fields` 为空。
- 来源映射：把关键事实/数字/论断到稿件位置的映射写入 `source_map`
  （如 `{"结论误差5%": "accepted.docx 段落16；原稿同文一致"}`）。

## 异常处理

| 情形 | 处置 |
| --- | --- |
| 稿件无法解析/加密损坏 | 不修复原文；status=failed，写明原因，保留已抽取的清单 |
| 指令锚点找不到 | 标 `human_confirmations`，跳过该条，不猜 |
| 指令与稿件内容冲突 | 按稿件事实为准，冲突写入 uncertainty 并请求人工确认 |
| 引用库/材料缺失 | 不补造；涉及条目标 partial 并说明 |
| soffice/pdftoppm 缺失 | 保留 DOCX，预览字段注明降级，status 可保持但需说明 |
| 超时预算紧张 | 先保证 result.json + 修订稿 + 台账落盘，再补预览 |

## 与其他方向的边界

本方向的核心资产是“原生修订 + 逐条台账 + 接受/拒绝变体”。引用重编号
（v2）、版本谱系（v3）、导出保真（v4）、漂移守卫（v5）是相邻能力；
本 Skill 仅做保真核验所必需的引用/格式检查，不做主动重编号。

## 最小调用示例（示意，非正式案例结果）

```bash
SKILL_DIR=/skills/weekly-skill
python3 $SKILL_DIR/scripts/workorder.py /input paras.json plan.json
python3 $SKILL_DIR/scripts/revisions_apply.py manuscript.docx plan.json out \
  --edits-json details.json
# 示意输出：{"ok": true, "counts": {"applied": 4, "verified": 1, "failed": 0}}
```
