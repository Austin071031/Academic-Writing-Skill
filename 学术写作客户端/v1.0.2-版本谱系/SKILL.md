---
name: academic-writing-version-lineage
description: 学术写作客户端·版本管理方向。当任务需要对学术稿件的多次修改保留版本谱系、做版本间差异对比与回退、杜绝无法对应来源的多份副本时使用。覆盖“接收稿件—内容寻址快照—谱系 manifest—定点修改—diff/回退—结构化结果”全闭环。
---

# 学术写作客户端 · 版本谱系（v3）

## 用途

把稿件的每一次状态（原稿、每次修改后、每次导出前）保存为**内容寻址的不可变
快照**（sha256 命名），用谱系 manifest 记录父子关系、来源与变更摘要。
任意两版本可段落级 diff；回退 = 检出旧快照，零丢失、零覆盖；
同一内容的重复快照自动去重，从机制上杜绝“无法对应来源的多个副本”。

适用条件：需要多次修改、版本对比或回退能力的学术写作任务；
单篇 DOCX 稿件为主。纯标准库实现，无 pip 依赖。

## 调用方式

```bash
SKILL_DIR="${SKILL_DIR:-/skills/weekly-skill}"
ls "${SKILL_DIR}/scripts"
```

## 执行流程

### 阶段 0：读取事实与契约

通读 `/input/case.json`、`task.md`、`organizer-edit-workorder.json`，
提取 `case_id` 与 `output_contract`；清点输入并识别主稿件。立即落盘部分
result.json（status=partial）。

### 阶段 1：初始化版本库并快照原稿

```bash
mkdir -p /app/work/originals /app/work/stage /app/work/vault
cp -a /input/. /app/work/originals/
python3 "${SKILL_DIR}/scripts/lineage.py" snapshot /app/work/originals/<主稿件>.docx \
  /app/work/vault --label original --source author
```

`lineage.json` 为谱系 manifest；快照文件以 sha256 命名存于 vault。
此后**每一次**产生新稿件状态（修改后、同步后、导出前）都必须立即快照：

```bash
python3 "${SKILL_DIR}/scripts/lineage.py" snapshot <新稿.docx> /app/work/vault \
  --label <语义标签> --parent <上版本rev> --source skill
```

### 阶段 2：指令锚定与定点修改

锚定与修改纪律同通用流程（workorder.py → edit_plan.json；
docxkit 的 replace_span / tracked_replace 最小改动）。
**每完成一个修改批次就快照一次**，parent 指向上一个版本 rev，
label 写明本批内容（如 `terminology-unify`）。

### 阶段 3：版本间 diff（版本对比证据）

```bash
python3 "${SKILL_DIR}/scripts/lineage.py" diff /app/work/vault <revA> <revB> \
  /app/work/stage/version_diff.json
```

diff 报告列出每个变化段落的原文与新文。把“原稿 → 交付稿”的 diff
摘要写入 result.json 的 `change_records`，这就是版本对比的可复核证据。
注意：新增段落会导致其后段落号位移，解读 diff 时以锚句内容为准，
不以位置号为准。

### 阶段 4：回退能力验证（有回退要求时）

```bash
python3 "${SKILL_DIR}/scripts/lineage.py" restore /app/work/vault <rev> \
  /app/work/stage/restored.docx
python3 "${SKILL_DIR}/scripts/lineage.py" verify /app/work/vault
```

restore 必须产出与快照 sha256 一致的文件；verify 校验全部快照完整。
把回退验证结果写入 result.json（`rollback_verified: true/false`）。

### 阶段 5：导出预览与归档

```bash
python3 "${SKILL_DIR}/scripts/render_preview.py" <最终稿>.docx /app/output/previews 3
cp <最终稿>.docx /app/output/revised_document.docx
cp /app/work/vault/lineage.json /app/output/version_lineage.json
```

### 阶段 6：结构化结果

```bash
python3 "${SKILL_DIR}/scripts/result_builder.py" /input/case.json /app/output/result.json \
  --status success \
  --set 'revised_document=/app/output/revised_document.docx' \
  --set 'version_lineage=/app/output/version_lineage.json' \
  --set 'change_records=["见 version_diff.json：N 个段落变化，全部对应指令条目"]'
```

交付稿必须能从 manifest 的 parent 链一路回溯到 author 原稿；
回溯链断裂（例如绕过 vault 直接改文件）是本方向的失败形态，发现即返工。

## 异常处理

| 情形 | 处置 |
| --- | --- |
| vault 磁盘不足 | 保留 manifest + 最近快照，旧快照可删但需在 manifest 标注 pruned |
| 快照文件损坏 | verify 检出 corrupted rev；若原稿快照损坏，从 /app/work/originals 重建 |
| 指令要求回退到输入前状态 | 输入前状态不存在于 manifest 时如实说明，不虚构 |
| 多稿件案例 | 每个稿件一个 vault（vault_<name>/） |

## 创新边界

基础 Agent 的典型失败是“交出一个新文件，原稿哪去了说不清”，或桌面上出现
`final.docx`、`final2.docx`、`final_真的最终.docx` 多个无法对应来源的副本。
内容寻址快照 + 谱系 manifest 让每个字节可校验（sha256）、每个版本有父、
每次回退有证据；这是版本管理方向相对“另存为”式编辑的实质方法改进。

## 最小调用示例（示意，非正式案例结果）

```bash
python3 $SKILL_DIR/scripts/lineage.py snapshot manuscript.docx vault --label original
# 示意：{"rev": "f35de3cb9be4", "sha256": "f35de...", ...}
python3 $SKILL_DIR/scripts/lineage.py diff vault f35de3cb 54001334
# 示意：{"changed_paragraphs": 19, "changes": [...]}
python3 $SKILL_DIR/scripts/lineage.py restore vault f35de3cb restored.docx
# 示意：{"ok": true, "sha256_verified": true}
```
