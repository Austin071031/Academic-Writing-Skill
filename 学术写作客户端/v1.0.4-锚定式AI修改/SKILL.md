---
name: academic-writing-anchored-editing
description: 学术写作客户端·AI 精准修改方向。当任务要求把自然语言修改指令落到具体句子或段落、控制改写幅度、避免未经许可的整段覆盖与语义漂移时使用。以“指令分解→锚点定位→最小改动→漂移守卫”四步闭环保证改得准、可追溯、不漂移，覆盖富文本格式保留与结构化结果交付。
---

# 学术写作客户端 · 锚定式 AI 修改（v5）

## 用途

解决基础 Agent 在“AI 修改”上的三个真实失败：**改得不在指定位置**（该改
第 2 章的句子动了第 4 章）、**整段推倒重写**（措辞层面指令被做成了结构
层面改写）、**语义漂移**（数字、术语、论断在改写中悄悄改变）。
本 Skill 的方法论是四步闭环：**指令分解 → 锚点定位 → 最小改动 → 漂移守卫**，
其中漂移守卫由脚本强制执行（锚定校验、改写幅度阈值、未授权改动检测、
数字守恒），不依赖模型自觉。

适用条件：自然语言修改指令 + DOCX 稿件；需要保留原样式、编号与结构。
纯标准库实现，无 pip 依赖。

## 调用方式

```bash
SKILL_DIR="${SKILL_DIR:-/skills/weekly-skill}"
ls "${SKILL_DIR}/scripts"
```

## 执行流程

### 阶段 0：读取事实与契约

通读 `/input/case.json`、`task.md`、`organizer-edit-workorder.json`，
提取 `case_id` 与 `output_contract`；清点输入识别主稿件。落盘部分
result.json（status=partial）。

### 阶段 1：保全原稿与结构摸底

```bash
mkdir -p /app/work/originals /app/work/stage
cp -a /input/. /app/work/originals/
python3 "${SKILL_DIR}/scripts/docxkit.py" inspect /app/work/originals/<主稿件>.docx \
  > /app/work/stage/manifest.json
python3 "${SKILL_DIR}/scripts/docxkit.py" dump /app/work/originals/<主稿件>.docx \
  > /app/work/stage/paras.json
```

### 阶段 2：指令分解（Agent 的语义工作集中于此）

把每条自然语言指令分解为**一条或多条原子改动**，写入 edit_details.json。
每条原子改动五要素：

```json
{
  "E1": {"type": "replace", "old": "…", "new": "…",
         "level": "措辞", "basis": "…依据与来源…"}
}
```

- `level` ∈ 措辞 / 术语 / 结构 / 引用 / 核对。指令只说措辞就只做措辞；
  想做更大层面改动而指令未授权 → 标 human_confirmations，不做。
- `old` 逐字取自原稿（锚定证据）；`new` 不得引入材料外事实、数字、引用。
- 分解纪律：一个原子改动只覆盖一处局部文本；预计改动字符占比超过所在段
  一半时，先拆条；拆不了就请求确认，而不是整段重写。
- 类型：replace（替换）/ delete（删除）/ insert_after（段后增补）/
  note（仅核对，不改写）。

### 阶段 3：锚点校验与最小改动落地

先用 workorder 做机器锚定，与分解结果互相印证：

```bash
python3 "${SKILL_DIR}/scripts/workorder.py" /input /app/work/stage/paras.json \
  /app/work/stage/edit_plan.json
python3 "${SKILL_DIR}/scripts/revisions_apply.py" \
  /app/work/originals/<主稿件>.docx /app/work/stage/edit_plan.json /app/work/stage \
  --edits-json /app/work/stage/edit_details.json
```

锚定纪律：机器锚点与分解的 old 不一致时以**原文逐字核查**为准；
找不到唯一锚点的改动不执行，进 human_confirmations。

### 阶段 4：漂移守卫（本方向核心机制）

```bash
python3 "${SKILL_DIR}/scripts/drift_guard.py" /app/work/originals/<主稿件>.docx \
  /app/work/stage/accepted.docx /app/work/stage/changes.json \
  /app/work/stage/drift_report.json
```

守卫报告四类结果，任一非空都必须处置后才能交付：
- `anchors.failed`：有改动的 old 在原稿中不存在（凭印象改写）→ 返工；
- `rewrite_warnings`：改写比超阈值（默认 0.5）→ 确认指令授权或拆条；
- `unauthorized_changes`：锚点邻近之外的段落发生变化 → 未授权改动，
  必须撤销或显式确认；
- `number_drift`：改写中数字消失且不在改动目标内 → 事实漂移，返工。

### 阶段 5：富文本保真与导出

```bash
python3 "${SKILL_DIR}/scripts/audit_diff.py" /app/work/originals/<主稿件>.docx \
  /app/work/stage/accepted.docx /app/work/stage/whitelist.txt \
  > /app/work/stage/fidelity.json
python3 "${SKILL_DIR}/scripts/render_preview.py" /app/work/stage/revised_tracked.docx \
  /app/output/previews 3
cp /app/work/stage/revised_tracked.docx /app/output/revised_document.docx
cp /app/work/stage/changes.json /app/output/change_log.json
```

富文本保留由实现层保证：跨 run 替换摊回原 run（格式属性不丢）、
只重写 document.xml 一个部件（styles/numbering/关系原字节保留）、
域结构与超链接不进入替换路径。

### 阶段 6：结构化结果

```bash
python3 "${SKILL_DIR}/scripts/result_builder.py" /input/case.json /app/output/result.json \
  --status success \
  --set 'revised_document=/app/output/revised_document.docx' \
  --set 'change_log=/app/output/change_log.json' \
  --set 'drift_report=/app/work/stage/drift_report.json' \
  --set 'human_confirmations=[]'
```

`status` 如实：守卫报告非空且未解决 → partial；`missing_fields` 为空。

## 异常处理

| 情形 | 处置 |
| --- | --- |
| 指令模糊、可多种解读 | 列出解读候选，选最保守（改动最小）的一种并在 basis 说明 |
| 指令与稿件事实冲突 | 以稿件事实为准，冲突写入 uncertainty + human_confirmations |
| 漂移守卫反复失败 | 退回该条为 note 并请求人工确认，不强行交付 |
| 材料不足以支撑新增内容 | 不新增；涉及条目标 skipped 并说明 |

## 创新边界

“让模型别整段重写”靠提示词说了多年仍不可靠；本方向把约束变成
**可执行的守卫**：锚定校验证明每处改动有原文出处，改写比阈值把
“控制改写幅度”变成数字，未授权改动检测把“不许动别处”变成机械判定，
数字守恒把“事实不漂移”变成集合比对。守卫报告本身即是“改得准、可追溯”
的可核验证据。

## 最小调用示例（示意，非正式案例结果）

```bash
python3 $SKILL_DIR/scripts/drift_guard.py before.docx after.docx changes.json report.json
# 示意：{"anchors": {"ok": 5, "failed": []}, "rewrite_warnings": [],
#       "unauthorized_changes": [], "number_drift": [], "verdict": "clean"}
```
