---
name: academic-writing-citation-collab
description: 学术写作客户端·引用协作方向。当任务涉及学术稿件的正文编号引用与参考文献表一致性（新增、删除、重排引用后的编号同步）、Vancouver 顺序编码审计、DOI 形态核验时使用。覆盖“接收稿件—引用依赖图—审计报告—同步重编号—保真导出—结构化结果”全闭环。
---

# 学术写作客户端 · 引用协作（v2）

## 用途

维护学术稿件的正文引用与参考文献表同步。以正文首次出现顺序为权威构建
**引用依赖图**，审计顺序编码制下的编号问题（乱序、缺号、未引用条目、
DOI 缺失），并做确定性重编号：重写正文引用、重排参考文献表、输出新旧对照。
所有变换由脚本机械执行，不留无法对应来源的多份副本。

适用条件：编号制引用（[n]、[n,m]、[n-m]）的中英文稿件；作者-年份制稿件
可先抽取做条目核对，编号同步仅对编号制执行。纯标准库实现，无 pip 依赖。

## 调用方式

```bash
SKILL_DIR="${SKILL_DIR:-/skills/weekly-skill}"
ls "${SKILL_DIR}/scripts"   # 确认脚本目录后再调用
```

## 执行流程

### 阶段 0：读取事实与契约

同通用流程：通读 `/input/case.json`、`task.md`、`organizer-edit-workorder.json`，
原样提取 `case_id` 与 `output_contract` 字段；清点输入文件并识别主稿件
与参考文献文件（.bib / .ris / 文内列表）。立即落盘部分 result.json。

### 阶段 1：保全原稿与结构摸底

```bash
mkdir -p /app/work/originals /app/work/stage
cp -a /input/. /app/work/originals/
python3 "${SKILL_DIR}/scripts/docxkit.py" inspect /app/work/originals/<主稿件>.docx \
  > /app/work/stage/manifest.json
```

### 阶段 2：引用依赖图与审计

```bash
python3 "${SKILL_DIR}/scripts/citation_sync.py" audit \
  /app/work/originals/<主稿件>.docx /app/work/stage/citation_audit.json
```

审计报告必查四类问题：`order-mismatch`（首次出现编号与位次不一致）、
`missing-reference`（引用了不存在的条目）、`uncited-reference`（条目未被
正文引用）、`doi-missing`（条目无 DOI）。**只报告、不静默修复**：
- 乱序编号是否重排，取决于任务指令；指令未要求时给出方案并标
  `human_confirmations`；
- 未引用条目不得擅自删除，列入确认项；
- 缺号引用是材料缺口，写入 uncertainty，不补造文献。

### 阶段 3：同步重编号（指令授权后执行）

先出方案供核对（不写文件）：

```bash
python3 "${SKILL_DIR}/scripts/citation_sync.py" plan \
  /app/work/originals/<主稿件>.docx /app/work/stage/reorder_plan.json
```

方案 `order_map` 以正文首次出现顺序为权威；确认后执行：

```bash
python3 "${SKILL_DIR}/scripts/citation_sync.py" sync \
  /app/work/originals/<主稿件>.docx /app/work/stage/citation_synced.docx \
  /app/work/stage/sync_report.json
```

脚本完成两件事：正文引用编号重写（跨 run 保留格式，区间自动压缩如
`[1-3]`）；参考文献表段落按新序重排并改编号前缀。`sync_report.json`
记录每一处 span 改写（段落号、旧值、新值），可逐条回溯。

若任务指令还包含措辞/结构修改（如 organizer-edit-workorder 中的其他条目），
在完成引用同步后的 `citation_synced.docx` 上继续按通用编辑流程处理，
每处改动沿用“锚定—最小—台账”纪律（docxkit.replace_span / tracked_replace）。

### 阶段 4：保真核验

```bash
python3 "${SKILL_DIR}/scripts/citation_sync.py" audit \
  /app/work/stage/citation_synced.docx /app/work/stage/post_audit.json
```

同步后 `order-mismatch` 应清零；`uncited-reference` 按确认项处理。
再跑 `audit_diff.py` 对比原稿与同步稿，确认表格/图片/公式/脚注等
结构要素零变化（白名单：引用编号与参考文献表为合法变换）。

### 阶段 5：导出预览与归档

```bash
python3 "${SKILL_DIR}/scripts/render_preview.py" /app/work/stage/citation_synced.docx \
  /app/output/previews 3
cp /app/work/stage/citation_synced.docx /app/output/revised_document.docx
cp /app/work/stage/sync_report.json      /app/output/citation_report.json
```

### 阶段 6：结构化结果

```bash
python3 "${SKILL_DIR}/scripts/result_builder.py" /input/case.json /app/output/result.json \
  --status success \
  --set 'revised_document=/app/output/revised_document.docx' \
  --set 'citation_report=/app/output/citation_report.json' \
  --set 'source_map={"引用编号": "citation_audit.json + sync_report.json 逐条可回溯"}'
```

`status` 如实：审计发现问题但指令未授权修复 → partial + human_confirmations；
编号制不适用（作者-年份制）→ partial 并说明。`missing_fields` 必须为空。

## 异常处理

| 情形 | 处置 |
| --- | --- |
| 无参考文献表/引用库缺失 | 不补造条目；status=partial，写明缺口 |
| 正文无编号引用（作者-年份制） | 只做 DOI/字段核对，编号同步标 not-applicable |
| 参考文献条目与正文引用数对不上 | 报告双侧清单，交人工确认，不猜映射 |
| 域代码内的引用（ENDNOTE 域等） | 不动域结构，只改显示文本；改不了就标 partial |

## 创新边界

基础 Agent 对“增删引用后全篇编号与文献表同步”基本无解：常见失败是只改正文
不改文献表、或重排后编号互相矛盾。本方向的依赖图方法把“正文首次出现序列”
作为唯一权威，重编号是图上的确定性重标定，新值可由旧值唯一解释
（`order_map` 即证据链），这是现有编辑方案难以稳定实现的能力。

## 最小调用示例（示意，非正式案例结果）

```bash
python3 $SKILL_DIR/scripts/citation_sync.py audit manuscript.docx audit.json
# 示意：{"issues": [{"kind": "order-mismatch", "num": 3, ...}]}
python3 $SKILL_DIR/scripts/citation_sync.py sync manuscript.docx synced.docx report.json
# 示意：{"ok": true, "spans_rewritten": 7, "issues": 1}
```
