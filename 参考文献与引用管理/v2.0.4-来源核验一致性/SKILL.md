---
name: citation-verification-audit
description: |
  来源核验与一致性检查（「对得上」）v2.0.4。触发：任务要求核验参考文献是否真实/
  是否编造、检查正文引用与所引文献是否对得上、审计引用编号一致性，或交付"参考文献
  体检报告/引用匹配核验报告/带 ⚠ 标注的审校稿"。不触发：编号重排、去重合并、
  格式重著录。用法：prep 生成匹配裁决工作单 → Agent 逐段写 match_verdicts.jsonl →
  finish 全部脚本化。产出：result.json、verification_report.json/md、
  annotated_manuscript.md、evidence_map.json、preview.html。默认离线可运行。
---

# v2.0.4｜来源核验与一致性检查（对得上）

**与父版差异**：父版 v1.0.4（attempt 89253，57 分）的六阶段压缩为三步；prep 生成
匹配裁决工作单（带引用段落 + 所引条目元数据并排呈现，省掉 Agent 反复对照文件），
Agent 的论断级裁决**保留**，条目体检/标注/报告全部脚本化。判据与父版一致。

## 三步流程

```bash
# 第 1 步：解析+生成匹配裁决工作单
python3 /skills/weekly-skill/scripts/run_pipeline.py --input /input --work /app/work --out /app/output --stage prep
# 第 2 步：读 /app/work/match_worksheet.md → 逐段写 /app/work/match_verdicts.jsonl
# 第 3 步：体检+标注+报告+组装+闸门
python3 /skills/weekly-skill/scripts/run_pipeline.py --input /input --work /app/work --out /app/output --stage finish
```

## 裁决核心（写 verdicts 时逐段套用）

- **四档**：supports（所引文献主题与结论直接支撑论断）/ partially（部分支撑或范围
  更窄）/ unrelated（主题无关）/ insufficient_evidence（材料不足，写明缺什么）。
- **只依据材料内信息**（条目题名/刊名/年份 + 正文论断句），不得凭记忆断言文献真伪；
  rationale 必须引用双方原文短语。
- 工作单 B 节列出的每个待裁决段落至少写一行；漏段会被引擎审计列入 missing_pids。

## 三条红线

1. **不凭印象判真伪**：本地体检 suspicious 只是启发式信号，最终结论以报告为准。
2. **不臆造联网核验**：默认离线记 unverified_offline/not_attempted，如实呈现。
3. **证据不足必标注**：材料不足的句子判 insufficient_evidence，不得强行 supports。

## 异常处置

| 异常 | 处置 |
|---|---|
| verdicts 缺失（超预算等） | finish 仅交付条目级体检报告，status=partial |
| 编号超出文献库范围 | 工作单即标 ⚠；引擎并入报告 out_of_range |
| 坏 verdict/坏 entry_id/空 rationale | 引擎审计逐条列出 issue，报告可见 |
| 联网核验（--online 需显式开启） | 默认离线；开启后 5 秒超时失败记 unverified_offline |

参考文档：`references/verdict_rubric.md`（四档判据+示例）、
`references/fabrication_heuristics.md`、`docs/USAGE.md`。
