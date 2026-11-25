# citation-verification-audit（v2.0.0：来源核验与一致性检查）

两层核验的引用审计 Skill：**条目级真实性体检**（引擎，确定性）× **论断级引用匹配**（Agent 四档裁决，引擎汇总留痕）。

## 用途

- 检查文献库条目"像不像编造"（DOI 语法、年份合理性、字段自洽、重复录入等启发式）。
- 逐句核对"正文论断 ↔ 所引文献"是否对得上（supports / partially / unrelated / insufficient_evidence）。
- 可选联网：逐条 DOI 请求 Crossref（5 秒超时，失败诚实记 unverified_offline）。
- 联动 cite_engine audit 输出引用编号一致性结论。
- 交付：verification_report.json/md（机读/人读）、annotated_manuscript.md（⚠ 标注审校稿）、evidence_map.json、result.json。

## 安装

把整个目录原样安装为 `/skills/weekly-skill` 即可；仅依赖 Python 3.8+ 标准库，无需 chmod +x。

## 快速开始（Harbor 运行时）

```bash
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 /skills/weekly-skill/scripts/parse_manuscript.py <稿件> --work /app/work
python3 /skills/weekly-skill/scripts/parse_library.py <文献库...> --work /app/work
# Agent：读 work/manuscript.json + work/library.json，写 work/match_verdicts.jsonl（见 SKILL.md Phase 2）
python3 /skills/weekly-skill/scripts/verify_engine.py --library /app/work/library.json --manuscript /app/work/manuscript.json --verdicts /app/work/match_verdicts.jsonl --work /app/work --out /app/output
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output --skill "citation-verification-audit v5.0.0" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```

完整步骤与自测记录见 docs/USAGE.md。

## 边界

- 只核验、只标注，**不改**稿件引用编号、不重著录文献表（修复请配合v1.0.0/2/3流程）。
- 本地体检的 suspicious 是"疑似"信号而非造假确证；确证需要联网核验（--online）或人工复核。
- 默认离线运行联网状态如实标注未核验；--online 受沙箱网络状况限制，逐条 5 秒超时降级。
