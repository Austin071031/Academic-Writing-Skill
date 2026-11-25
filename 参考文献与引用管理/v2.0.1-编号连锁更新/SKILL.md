---
name: citation-renumber-chain
description: |
  参考文献编号连锁更新引擎（「编得顺」）v2.0.1。触发：任务书要求对顺序编码制稿件做
  引用条目编辑（删除文献/调序/插入库中条目/合并去重），并要求正文编号、文末列表、
  图注/表注/附录/脚注引用全部同步、编号连续无缺口。不触发：从零撰写新引文；
  文献去重归并；纯格式转换。用法：prep → 写 edit_ops.json → finish（三步）。
  产出：result.json、edited_manuscript.md、references.md/json、renumber_report.md、
  consistency_audit.json、preview.html。
---

# v2.0.1｜编号连锁更新（编得顺）

**与父版差异**：父版 v1.0.1（attempt 89250，63 分）的六阶段压缩为三步；edit_ops 的
**Agent 判断完整保留**（v1.1.0 全自动版 50 分证明去掉判断会降分），机械环节全部
脚本化。引擎判据与父版逐字节一致。

## 三步流程（严格按序，共 3 次工具调用 + 1 个 JSON 文件）

```bash
# 第 1 步：预检+解析，stdout 末尾打印当前文末列表与 edit_ops 写法
python3 /skills/weekly-skill/scripts/run_pipeline.py --input /input --work /app/work --out /app/output --stage prep
# 第 2 步：读第 1 步输出与 task.md，写 /app/work/edit_ops.json（只写任务书明确要求的操作，
#          无编辑要求写 []；schema 与 20 例见 references/edit_ops_schema.md）
# 第 3 步：引擎连锁更新+审计+组装+闸门
python3 /skills/weekly-skill/scripts/run_pipeline.py --input /input --work /app/work --out /app/output --stage finish
```

## 三条红线

1. **不臆造文献/元数据**：条目只能来自输入文献库或稿件自带列表。
2. **不臆造核验结果**：终检以 `work/renumber_report.json` 的 `PASS` 字段为准。
3. **改编号必须走引擎**：禁止手工改正文/图注/列表里的 `[n]` 数字；若第 3 步报悬空，
   唯一允许的人工改动是改写 `work/manuscript.json` 中相关句子的**语义**（删引/改引），
   然后重跑第 3 步。

## 异常处置

| 异常 | 处置 |
|---|---|
| 删除的条目仍被引用（悬空） | 引擎 FAIL 并列悬空清单 → 先尝试改写句子重跑 finish；仍 FAIL 时编排器自动移除悬空标记并留痕（记 change_log/uncertainty） |
| 任务书指代不清（如"删掉那篇综述"对应多条） | 不写进 edit_ops，写入 `work/manual_confirmations.json`，交付 partial 说明 |
| 著者-出版年稿件 | 引擎自动分流：不重排，仅查列表排序并标注 stale |
| 文献库为空/稿件无法解析 | 如实记录 exceptions，status=partial |
| 超预算 | 任何时候中断都有 init_result 骨架；edit_ops 写不完就先跑 finish（恒等映射交付） |

参考文档：`references/edit_ops_schema.md`（schema+20 例）、`references/chain_update.md`
（连锁规则）、`references/invariant_checklist.md`（终检清单）、`docs/USAGE.md`（完整说明）。
