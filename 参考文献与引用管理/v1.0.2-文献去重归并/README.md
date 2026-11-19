# v1.0.2｜文献去重与条目归并（ref-dedup-merge）

对文献库做**可解释的多信号去重**：同一文献的中英文题名、预印本与正式版、
期刊版与会议版、不同数据库导出差异，被量化为成对相似信号（题名 3-gram
Jaccard、DOI 一致、年份差、作者姓氏重合、刊会相似、类型兼容度），分三档处置
（自动合并 / 候选交 Agent 裁决 / 禁止合并保护），每个合并决定附带完整证据
信号与理由，杜绝误合并同名作者的不同文献。

## 安装

本目录整体复制为 `/skills/weekly-skill` 即可（自包含；scripts/ 含 8 个共享核心
脚本 + 专属 `dedup_engine.py`，全部仅依赖 Python3 标准库）。

## 快速开始

```bash
# 在 Harbor 运行时（/input、/app/work、/app/output 由环境提供）：
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 /skills/weekly-skill/scripts/parse_library.py <文献库文件...> --work /app/work
python3 /skills/weekly-skill/scripts/parse_manuscript.py <稿件文件 如有> --work /app/work
python3 /skills/weekly-skill/scripts/dedup_engine.py candidates --library /app/work/library.json --work /app/work
# Agent 读 work/merge_candidates.json，逐组写 work/merge_decisions.jsonl（见 SKILL.md Phase 3）
python3 /skills/weekly-skill/scripts/dedup_engine.py apply --library /app/work/library.json --decisions /app/work/merge_decisions.jsonl --work /app/work --out /app/output --manuscript /app/work/manuscript.json
python3 /skills/weekly-skill/scripts/cite_engine.py render --records /app/output/library_deduped.json --style gbt2015_numeric --out /app/output/references.md
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --skill "ref-dedup-merge v3.0.0" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --expect-status success
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```

## 产物

| 产物 | 位置 | 说明 |
|---|---|---|
| 去重后文献库 | /app/output/library_deduped.json | 合并后条目 + merged_from/dropped 溯源 |
| 合并报告（人读） | /app/output/merge_report.md | 每组判据信号表+字段来源+差异说明 |
| 合并报告（机读） | work/merge_report.json | signals/field_sources/diff_notes/rationale |
| GB/T 参考文献表 | /app/output/references.md | cite_engine render gbt2015_numeric |
| 编号映射 | work/dedup_mapping.json | drop→keep 的 rid/编号映射 + limits |
| 总结果 | /app/output/result.json | 含 output_contract 字段与证据链 |

## 边界

- 只做"归并与解释"，不臆造元数据、不核验文献真实性（那是v1.0.4）；
- 不做正文编号重排（输出映射交给v1.0.1 的 renumber 流程）；
- 跨语言是否同译由 Agent 依据判据裁决，引擎只提供信号与提示；
- 纯标准库、无网络依赖。
