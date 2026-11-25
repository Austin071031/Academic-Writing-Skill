---
name: ref-dedup-merge
description: |
  文献去重与条目归并（「收得净」）v2.0.2。触发：任务要求对文献库/参考文献表去重、
  合并同一文献的多个版本（中英文题名、预印本与正式版、期刊与会议版、不同数据库
  导出差异）并给出可解释合并依据。不触发：引用编号重排、来源核验、格式转换。
  用法：prep 生成裁决工作单 → Agent 逐组写 merge_decisions.jsonl → finish 全部脚本化。
  产出：result.json、library_deduped.json、merge_report.md（信号表+字段来源+差异说明）、
  references.md、dedup_mapping.json、preview.html。
---

# v2.0.2｜文献去重与条目归并（收得净）

**与父版差异**：父版 v1.0.2（attempt 89251，57 分）的六阶段压缩为三步；prep 生成
裁决工作单（候选组+六信号一屏呈现），Agent 的合并裁决**保留**，执行与报告全部
脚本化。引擎判据（信号阈值/三档/字段择优）与父版逐字节一致。

## 三步流程

```bash
# 第 1 步：解析+候选扫描+生成裁决工作单
python3 /skills/weekly-skill/scripts/run_pipeline.py --input /input --work /app/work --out /app/output --stage prep
# 第 2 步：读 /app/work/verdict_worksheet.md → 逐组写 /app/work/merge_decisions.jsonl
# 第 3 步：合并执行+报告+组装+闸门
python3 /skills/weekly-skill/scripts/run_pipeline.py --input /input --work /app/work --out /app/output --stage finish
```

## 裁决核心（写 decisions 时逐组套用）

- **合并**：中英文同译、预印本↔正式版、期刊↔会议同研究——题名实质相同+作者重合+
  年份差≤1（对照工作单信号值）；合并保留正式版信息，arXiv 号进 extra_fields。
- **不合并**：同名作者同一年但题名主题不同（疑似同名不同文）；两个不同 DOI 均存在；
  工作单「保护对」列出的组合——一律 keep_separate 并写明依据。
- **拿不准**：keep_separate + rationale 写明存疑点（宁可不合并，不可误合并）。

## 三条红线

1. **不臆造元数据**：合并只做字段择优与并集补全，每字段来源可追溯。
2. **不臆造核验结果**：合并正确性以 `merge_report.md` 的信号表为证据。
3. **候选组必须逐组裁决**：漏裁决的组会在 stats 中体现，不得跳过。

## 异常处置

| 异常 | 处置 |
|---|---|
| 跨语言条目（中英文是否同译） | 引擎只给 hint，由 Agent 读题名裁决 |
| decisions 缺失 | finish 仅交付候选报告，status=partial |
| 文献库无重复 | 候选 0 组，正常交付审计基线（status=success） |
| 保护对被误裁决 merge | 引擎 apply 硬校验拒绝并记 exceptions |

参考文档：`references/dedup_criteria.md`（阈值表+正反例含同名陷阱）、
`references/field_reconciliation.md`、`docs/USAGE.md`。
