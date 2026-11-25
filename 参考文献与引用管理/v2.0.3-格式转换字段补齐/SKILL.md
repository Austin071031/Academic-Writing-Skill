---
name: ref-format-converter
description: |
  文献库格式转换与字段补齐审计 v2.0.3（全自动单命令）。触发：任务要求把
  BibTeX/RIS/EndNote/CNKI 等导出转换为 GB/T 7714—2015（顺序编码制或著者-出版年）、
  APA 7、Vancouver，或要求"整理参考文献格式/补齐缺失字段/统一中英文标点/回转导出
  bibtex/ris"。不触发：文献真伪核验、论断-引用匹配、去重合并。用法：一条命令跑完。
  产出：result.json、converted_refs.txt、references.md、converted.bib、converted.ris、
  field_audit.json、convert_report.md、preview.html。
---

# v2.0.3｜格式转换与字段补齐

**与父版差异**：父版 v1.0.3（attempt 89252，49 分，五方向最低）的失分主因推断为
流程未走完/交付不完整。本方向判断环节本就为零（转换是确定性的），v2.0.3 把
**目标规范识别也脚本化**（task.md 关键词自动判定），一条命令完成全部工作，
彻底消除"没走完"的可能。映射表与标点规则与父版一致。

## 唯一需要执行的命令

```bash
python3 /skills/weekly-skill/scripts/run_pipeline.py --input /input --work /app/work --out /app/output
```

目标规范自动判定：task.md 提到 GB/T 7714 著者-出版年→`gbt2015_author`；GB/T 7714/
国标/顺序编码→`gbt2015_numeric`；APA→`apa7`；Vancouver/IEEE→`vancouver`；
未指明→默认 `gbt2015_numeric` 并记 uncertainty。如需人工指定：`--to apa7`。

## 跑完之后 Agent 只做一件事

读 `/app/output/convert_report.md` 与 `field_audit.json`：确认目标规范判定正确、
缺字段条目全部标注 not_provided（材料未提供，**绝不臆造补齐**）。判定有误时用
`--to <正确规范>` 重跑同一条命令。

## 三条红线

1. **不臆造字段**：缺卷/期/页/DOI 标 not_provided；跨条目互补仅限同规范化标题+
   类型兼容+年份一致的条目，且注明来源 rid。
2. **不失真**：DOI、卷期页、文献类型标识逐条保留；标点按条目语种规范化。
3. **不臆造核验**：字段保留率以 `field_audit.json` 为准。

## 异常处置

| 异常 | 处置 |
|---|---|
| 文献库为空 | exceptions 记录，status=partial |
| 中英文混排 | 按条目 language 分别处理标点（references/punctuation_rules.md） |
| 未映射字段 | 保留进 extra_fields 并在报告说明 |
| 联网补齐（--try-online 需显式开启） | 默认不联网；开启后 5 秒超时失败如实记 unverified |

参考文档：`references/format_specs/`（四种规范数据文件）、
`references/punctuation_rules.md`、`docs/USAGE.md`。
