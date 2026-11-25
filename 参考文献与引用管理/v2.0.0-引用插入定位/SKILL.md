---
name: citation-placement-skill
description: |
  论断级引用插入与定位（「挂得对」）v2.0.0。触发：用户同时提供学术稿件与文献库，
  并要求"插入引用/补引文/调整引用位置/整理参考文献表"。不触发：纯问答、无文献库、
  编号重排（那是 citation-renumber-chain）。用法：prep 生成论断工作单 → Agent 写
  citation_decisions.jsonl → finish 全部脚本化。产出：result.json、
  edited_manuscript.md、references.md/json、consistency_audit.json、preview.html。
---

# v2.0.0｜引用插入与定位（挂得对）

**与父版差异**：父版 v1.0.0（attempt 89249，53 分）的六阶段压缩为三步；prep 直接生成
论断工作单（段落+文献目录一屏呈现，省掉 Agent 反复翻文件），rubric 核心内联到本文件
（不再依赖 Agent 主动读 references/）。引擎判据与父版一致。

## 三步流程

```bash
# 第 1 步：预检+解析+生成论断工作单
python3 /skills/weekly-skill/scripts/run_pipeline.py --input /input --work /app/work --out /app/output --stage prep
# 第 2 步：读 /app/work/claims_worksheet.md → 写 /app/work/citation_decisions.jsonl
# 第 3 步：插入+重排+审计+组装+闸门
python3 /skills/weekly-skill/scripts/run_pipeline.py --input /input --work /app/work --out /app/output --stage finish
```

## 论断判定核心（写 decisions 时逐条套用）

**需要引用的句子**：量化事实（数字/单位/阈值）；他人已发表的结论或方法沿袭；争议性或
反直觉论断；任务书明确要求引用的位置。
**不需要引用**：作者自己的新结果；公知常识；承上启下过渡句。
**位置**：插在承载论断的那句话句末（终结标点前），**禁止整段末尾堆引用**；
一句多引用 `[n,m]`；多篇连续用 `[n-m]`。
**来源约束**：entry_ids 只能选工作单 B 节列出的库记录 id；sentence 必须从段落原文
逐字复制（定位失败会进 exceptions，不得改写后插入）。

## 三条红线

1. **不臆造文献/元数据**：引用只能挂到文献库真实条目上。
2. **不臆造核验结果**：编号连续性与错放审计以 `work/placement_audit.json` /
   `consistency_audit.json` 为准。
3. **材料不足不硬挂**：没有合适条目支撑的论断，不挂引用，写入
   `work/manual_confirmations.json`。

## 异常处置

| 异常 | 处置 |
|---|---|
| decisions 缺失（超预算等） | finish 以空决策交付原稿+文献表审计基线，status=partial |
| sentence 定位失败 | 引擎记入 exceptions 并跳过该条，不臆造插入位置 |
| 著者-出版年稿件 | decisions 中 form 写 author_year，引擎自动处理同名同年 a/b 消歧 |
| 文献库为空 | 无法挂引，如实记录，status=partial |

参考文档：`references/claim_rubric.md`（完整判定细则+正反例）、
`references/placement_rules.md`（位置/多引/标点）、`docs/USAGE.md`。
