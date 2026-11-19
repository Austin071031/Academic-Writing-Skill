# USAGE：完整调用步骤、输入输出与自查方法

## 1. 调用步骤（逐字命令）

以下 `<SKILL>` 为 Skill 安装目录（评测时 `/skills/weekly-skill`）。本仓库自测时以
`/tmp/tc` 为例：`--case /tmp/tc/input/case.json --input-dir /tmp/tc/input --work /tmp/tc/work --out /tmp/tc/output`。

```bash
# Phase 0 预检（超时空手保护）
python3 <SKILL>/scripts/init_result.py --case /tmp/tc/input/case.json --out /tmp/tc/output
python3 <SKILL>/scripts/inspect_case.py --case /tmp/tc/input/case.json --task /tmp/tc/input/task.md --input-dir /tmp/tc/input --work /tmp/tc/work

# Phase 1 解析（路径从 work/inspection.json 的 candidates 取）
python3 <SKILL>/scripts/parse_manuscript.py /tmp/tc/input/manuscript.md --work /tmp/tc/work
python3 <SKILL>/scripts/parse_library.py /tmp/tc/input/refs.bib --work /tmp/tc/work

# Phase 2（Agent）：读 work/manuscript.json + work/library.json，
#   逐句裁决全部带引用正文段落，写 work/match_verdicts.jsonl（格式见 SKILL.md Phase 2）

# Phase 3 引擎汇总（默认离线）
python3 <SKILL>/scripts/verify_engine.py --library /tmp/tc/work/library.json --manuscript /tmp/tc/work/manuscript.json --verdicts /tmp/tc/work/match_verdicts.jsonl --work /tmp/tc/work --out /tmp/tc/output
# 可选联网核验（逐条 DOI，Crossref，5 秒超时，失败诚实记 unverified_offline）：
python3 <SKILL>/scripts/verify_engine.py --library /tmp/tc/work/library.json --manuscript /tmp/tc/work/manuscript.json --verdicts /tmp/tc/work/match_verdicts.jsonl --work /tmp/tc/work --out /tmp/tc/output --online

# Phase 4-5 组装/终检/预览
python3 <SKILL>/scripts/assemble_result.py --work /tmp/tc/work --out /tmp/tc/output --skill "citation-verification-audit v5.0.0" --status success
python3 <SKILL>/scripts/validate_output.py --out /tmp/tc/output
python3 <SKILL>/scripts/render_previews.py --out /tmp/tc/output
```

## 2. 输入

| 输入 | 必需 | 说明 |
|---|---|---|
| case.json | 是 | case_id + output_contract |
| task.md | 是 | 任务说明 |
| 稿件（md/txt/tex/docx/pdf） | 是 | parse_manuscript.py 解析为段落+引用标记 |
| 文献库（bib/ris/enw/ciw/csv/json/GB-T 文本） | 是 | parse_library.py 统一为 R 编号记录 |
| work/match_verdicts.jsonl | 是（Agent 写） | 四档裁决；缺漏由引擎审计并标注 |

## 3. 输出（/app/output）

| 文件 | 内容 |
|---|---|
| verification_report.json | 机读：entries[].checks[]（每项 verdict+evidence）、online_status、claims[]、coverage、consistency、summary |
| verification_report.md / report.md | 人读：可疑条目表、联网状态表、不匹配论断表、证据不足清单、覆盖审计、编号一致性、总体结论 |
| annotated_manuscript.md / edited_manuscript.md | 在不匹配/证据不足/部分匹配论断句后插 `<!-- ⚠ verdict: ... -->`；缺裁决段落插 `⚠ 缺裁决` 注释；原文不动 |
| consistency_audit.json | cite_engine audit 结果（复制） |
| result.json | case_id、status、outputs、evidence_map、uncertainty、exceptions、stats |
| preview.html（尽力 preview.pdf） | 标注稿+报告预览 |

## 4. 端到端自测记录（2026-11-19，/tmp/tc 合成案例 SYNTH-V5）

输入：`/tmp/tc/input/`（case.json、task.md、manuscript.md 两个正文段落 4 处数字引用、
refs.bib 四条：R002 为疑似编造条目——年份 2031、journal/卷/期/页全空、DOI `10.999/…` 非法）。

### Phase 0-1 实测输出

```
[init_result] 骨架已写入 /tmp/tc/output/result.json (case_id=SYNTH-V5)
[inspect_case] case_id=SYNTH-V5 材料=5 稿件候选=1 文献库候选=2 样式=numeric
[parse_manuscript] 5 段, 5 个引用标记, 样式=['numeric']
[parse_library] refs.bib: 4 条 (bibtex)  共 4 条 -> /tmp/tc/work/library.json
```

### Phase 2（手写 match_verdicts.jsonl，覆盖 2 个正文段落共 4 句）

```jsonl
{"pid": "P002", "sentence": "硅基负极的理论比容量高达 4200 mAh/g，远超石墨负极的 372 mAh/g", "entry_ids": ["R001"], "verdict": "supports", "rationale": "条目题名 'Silicon Anodes for Lithium-Ion Batteries: A Review' 为硅负极综述，可支撑论断'理论比容量高达 4200 mAh/g'的领域共识性数值"}
{"pid": "P002", "sentence": "硅在嵌锂时体积膨胀超过 300%，导致材料粉化失效", "entry_ids": ["R003"], "verdict": "supports", "rationale": "条目题名 'Volume Expansion of Silicon Electrodes' 与论断'体积膨胀超过 300%'直接对应"}
{"pid": "P003", "sentence": "Chan 等人报道了硅纳米线在循环中保持结构完整", "entry_ids": ["R002"], "verdict": "insufficient_evidence", "rationale": "论断点名 'Chan 等人'，但 R002 作者为 'Doe, Jane; Roe, Richard' 且条目无摘要；缺：Chan 对应的文献条目，仅有题名不足以确认'循环中保持结构完整'"}
{"pid": "P003", "sentence": "石墨烯包覆可显著提升循环稳定性", "entry_ids": ["R004"], "verdict": "unrelated", "rationale": "论断主题为'石墨烯包覆提升循环稳定性'，而 R004 题名 'Vapor-Liquid-Solid Growth of Semiconductor Nanowires' 是纳米线生长方法学，主题对不上"}
```

### Phase 3 实测输出（offline）

```
[verify_engine] 条目 4（可疑 1） 论断 4 缺漏段落 无 结论=issues_found 模式=offline
```

- `summary`：`n_entries=4, n_suspicious_entries=1`（R002 命中 doi_syntax / year_plausibility /
  field_conflict 三项 suspicious）、`claim_verdict_counts={supports:2, insufficient_evidence:1, unrelated:1}`、
  `missing_pids=[]`、`conclusion=issues_found`。
- 联网状态（离线如实）：R001/R003=`not_attempted_offline_mode`，R002=`online_skipped_no_doi_or_invalid`，
  R004=`online_skipped_no_doi`。
- `annotated_manuscript.md`：P003 两句后分别插入
  `<!-- ⚠ verdict: insufficient_evidence | entries: R002 | rationale: … -->` 与
  `<!-- ⚠ verdict: unrelated | entries: R004 | rationale: … -->`，其余原文逐字保留。

### Phase 4-5 实测输出

```
[assemble] status=success outputs=['edited_manuscript', 'report', 'verification_report', 'consistency_audit'] -> /tmp/tc/output/result.json
[validate] PASS (status=success)
[render_previews] preview.html 已生成
```

### 阴性自测（同一案例）

- 空 match_verdicts.jsonl → `missing_pids=['P002','P003']`、`conclusion=incomplete`，
  标注稿在两段落行尾插 `<!-- ⚠ verdict: insufficient_evidence | entries: ∅ | rationale: 【引擎审计】该带引用段落缺少 Agent 裁决行… -->`。
- 坏行 `{"verdict":"yes","entry_ids":["R999"],"rationale":""}` → 审计记
  `verdict_bad_value / verdict_bad_entry / verdict_no_rationale` 三类 issue。
- `--online` 模式（沙箱无网络）→ R001/R003 如实记 `unverified_offline`，其余产物不受影响。

## 5. 自查方法

1. `python3 -m py_compile <SKILL>/scripts/*.py` 全通过。
2. 报告 `summary.missing_pids` 应为 `[]`；非空说明 Phase 2 漏判，需回补齐。
3. 可疑条目表每条 evidence 可人工复核（正则/年份值/缺失字段名均在材料内可查）。
4. `validate_output.py` 输出 `PASS`；`render_previews.py` 必出 `preview.html`。
5. 离线报告必须出现诚实声明"未核验 ≠ 造假"；联网报告的 `unverified_offline` 比例反映网络状况。
