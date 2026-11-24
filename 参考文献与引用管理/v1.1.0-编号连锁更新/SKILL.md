---
name: citation-renumber-chain
description: |
  参考文献编号连锁更新引擎（「编得顺」）v1.1.0 快轨版。什么时候触发：任务书要求对
  顺序编码制（numeric / GB/T 7714 顺序编码）稿件做引用条目编辑——删除文献、调序、
  插入文献库条目、两章合并去重，并要求正文编号、文末列表、图注/表注/附录/脚注引用
  全部同步、编号连续无缺口时。什么时候不触发：从零撰写新引文；文献去重归并；
  纯格式转换。用法：一条命令跑完全流水线（详见正文）。产出物：
  /app/output/result.json（含 output_contract 全字段与 case_id）、edited_manuscript.md、
  references.md/json、renumber_report.md、consistency_audit.json、preview.html。
---

# v1.1.0｜编号连锁更新（编得顺）——快轨版

**相对父版 v1.0.1（attempt 89250，63 分）的唯一机制增量**：把 Phase 0-5 六条命令编排为
**一条命令全流水线** `scripts/run_pipeline.py`（预检→解析→文末列表基准抽取→任务书编辑
指令自动派生→引擎连锁更新→悬空自动处置→审计→契约组装→闸门→预览），彻底解决回放中
"流程过长导致主产物不完整"的失分点。引擎本体与判据与父版完全一致。

## 唯一需要执行的命令

```bash
python3 /skills/weekly-skill/scripts/run_pipeline.py --input /input --work /app/work --out /app/output
```

跑完即交付完成。命令会打印 `[1/5]…[5/5]` 各阶段摘要；stdout 出现 `INVARIANTS: PASS`
且末行 `[run_pipeline] DONE` 即成功。

## 跑完之后 Agent 做什么（2 步即可，禁止逐项手工跑子命令）

1. **读** `/app/output/renumber_report.md`：确认操作清单、映射表、终检结论。
2. **读** `/app/work/manual_confirmations.json`（若存在）：把其中的"任务书指令未能自动
   定位"条目原样写入 result.json 说明——不得自行猜测执行。

## 三条红线

1. **不臆造文献/元数据**：条目只能来自输入文献库或稿件自带列表。
2. **不臆造核验结果**：终检以 `work/renumber_report.json` 的 `PASS` 字段为准。
3. **改编号必须走引擎**：禁止手工改正文/图注/列表里的 `[n]` 数字；对正文唯一允许的
   人工改动是改写句子语义（删引/改引），改完重跑命令。

## 人工覆盖（仅当自动派生明显不符任务书时才用，普通案例不需要）

```bash
# 第一步：只跑到解析与派生为止
python3 /skills/weekly-skill/scripts/run_pipeline.py --input /input --work /app/work --out /app/output --stage prep
# 第二步：人工检查/重写 /app/work/edit_ops.json（schema 见 references/edit_ops_schema.md），
# 再跑收尾（检测到人工 edit_ops.json 时自动派生被跳过）
python3 /skills/weekly-skill/scripts/run_pipeline.py --input /input --work /app/work --out /app/output --stage finish
```

## 异常处置表

| 异常 | 流水线行为 |
|---|---|
| 任务书无编号编辑指令 | 恒等映射交付 + 审计报告；删除/插入指令无法唯一定位时写入 manual_confirmations，**不猜** |
| 删除的条目仍被正文引用 | 引擎列悬空 → 自动移除悬空正文标记（全程留痕 change_log，语义复核记 uncertainty）→ 重跑引擎 |
| 字段缺失/DOI 失败 | 不阻断；对应条目如实缺字段，记 uncertainty.json |
| 文献库为空 | 以稿件自带列表为基准；列表也无 → status=partial + exceptions 说明 |
| 稿件无法解析 | 跳过引擎，交付案例侦察 + exceptions，status=partial |
| 超预算 | 本命令是单命令，一次调用即可交付；任何时候中断都已有 init_result 骨架保底 |

## 参考文档

- `references/edit_ops_schema.md`：edit_ops 完整 schema 与 20 个例子
- `references/chain_update.md`：连锁更新规则（六类位置同步、区间压缩、一句多引）
- `references/invariant_checklist.md`：五项不变量终检清单
- `references/worked_example.md`：合成示例端到端
- `docs/USAGE.md`：完整使用说明与自查方法
