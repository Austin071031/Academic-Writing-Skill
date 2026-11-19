# USAGE｜完整调用步骤（v1.0.1 相关工作分组比较）

与 v1.0.0 共享同一管线，差异在 Phase 3 的登记文件与 Phase 4 的分组引擎。

## 1. 环境与逐步执行

环境与路径同 v1.0.0（见共享 README）。执行序列：

```bash
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_manuscript.py <稿件> --work /app/work
python3 $S/parse_library.py <文献库...> --work /app/work
python3 $S/parse_notes.py <笔记...> --work /app/work
python3 $S/extract_facts.py --work /app/work
```

Agent 写作阶段登记：evidence_map.json、grouping.json、comparison_rows.jsonl、
draft_rl.md、draft_intro.md、claim_bindings.jsonl（格式见 SKILL.md Phase 3 与 references/）。

```bash
python3 $S/group_related_work.py --work /app/work --out /app/output
python3 $S/build_deliverables.py --work /app/work --out /app/output
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json --skill "related-work-grouping v1.0.1" --status success
python3 $S/validate_output.py --out /app/output --expect-status success
python3 $S/render_previews.py --out /app/output
```

## 2. 输出文件

related_work.md、comparison_matrix.md（引擎渲染）、introduction.md、references.md、
evidence_map.json、build_report.json、version_report.json（分组审计）、result.json、preview.html。

## 3. 自查要点

- version_report.json：ungrouped_cited / duplicates / chronological_suspect 全空；
  matrix_missing_for 越小越好（关键条目必须填）。
- build_report.json：锚点全解析、绑定 ≥90%、四要素全 true、无手写编号。
- 转述抽查：comparison_matrix 的"数据与评价"列数字与笔记逐字一致。

## 4. 失败处理

validate 非零 → 按 FAIL 信息修复；分组覆盖问题 → 按 version_report 的 ungrouped 清单补组后重跑；
幂等可重跑。
