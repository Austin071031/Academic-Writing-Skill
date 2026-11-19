# Minimal Example（示例，非正式案例结果）

最小输入 → 调用 → 示意输出。合成数据，仅演示接口与产物形态。

## 输入

`case.json`：

```json
{"case_id": "DEMO-01", "output_contract": {"result": null, "evidence": null, "status": null}}
```

`manuscript.md`：

```markdown
# 钙钛矿太阳能电池的稳定性

钙钛矿电池效率已突破 25%，但湿度稳定性仍是瓶颈 [1]。
封装技术可将寿命延长至 10000 小时 [2]。

## 参考文献

[1] 张三. 钙钛矿综述[J]. 太阳能学报, 2021, 42(3): 1-10.
```

`refs.bib`：

```bibtex
@article{perovskite_review,
  title = {Perovskite Solar Cells: A Review},
  author = {Zhang, San}, year = {2021},
  journal = {太阳能学报}, volume = {42}, number = {3}, pages = {1-10},
  doi = {10.19912/j.ctp.2021.03.001}}
@article{stability_fake,
  title = {Ultrastable Encapsulation for 50000 Hours},
  author = {Doe, Jane}, year = {2027},
  journal = {}, volume = {}, number = {}, pages = {},
  doi = {10.1/short}}
```

## 调用（离线）

```bash
python3 <SKILL>/scripts/init_result.py --case /input/case.json --out /app/output
python3 <SKILL>/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 <SKILL>/scripts/parse_manuscript.py /input/manuscript.md --work /app/work
python3 <SKILL>/scripts/parse_library.py /input/refs.bib --work /app/work
# Agent 写 work/match_verdicts.jsonl（2 句，覆盖 P002）：
python3 <SKILL>/scripts/verify_engine.py --library /app/work/library.json --manuscript /app/work/manuscript.json --verdicts /app/work/match_verdicts.jsonl --work /app/work --out /app/output
python3 <SKILL>/scripts/assemble_result.py --work /app/work --out /app/output --skill "citation-verification-audit v5.0.0" --status success
python3 <SKILL>/scripts/validate_output.py --out /app/output
python3 <SKILL>/scripts/render_previews.py --out /app/output
```

Agent 写的 `work/match_verdicts.jsonl`：

```jsonl
{"pid": "P002", "sentence": "钙钛矿电池效率已突破 25%，但湿度稳定性仍是瓶颈", "entry_ids": ["R001"], "verdict": "supports", "rationale": "条目题名 'Perovskite Solar Cells: A Review' 为钙钛矿综述，可支撑'效率突破25%、湿度稳定性是瓶颈'的综述性论断"}
{"pid": "P002", "sentence": "封装技术可将寿命延长至 10000 小时", "entry_ids": ["R002"], "verdict": "insufficient_evidence", "rationale": "R002 题名 'Ultrastable Encapsulation for 50000 Hours' 谈封装寿命但数值为 50000 小时且年份 2027 晚于当前；条目无摘要，缺：可确认'10000 小时'结论的字段依据"}
```

## 示意输出（关键片段）

```
[verify_engine] 条目 2（可疑 1） 论断 2 缺漏段落 无 结论=issues_found 模式=offline
```

`verification_report.json → summary`：

```json
{"n_entries": 2, "n_suspicious_entries": 1, "claim_verdict_counts": {"supports": 1, "insufficient_evidence": 1},
 "missing_pids": [], "conclusion": "issues_found"}
```

`annotated_manuscript.md`（片段）：

```markdown
钙钛矿电池效率已突破 25%，但湿度稳定性仍是瓶颈 [1]。 封装技术可将寿命延长至 10000 小时 [2] <!-- ⚠ verdict: insufficient_evidence | entries: R002 | rationale: R002 题名 'Ultrastable Encapsulation for 50000 Hours' 谈封装寿命但数值为 50000 小时且年份 2027 晚于当前；缺：可确认'10000 小时'结论的字段依据 -->。
```

`verification_report.md` 可疑条目表（片段）：

```
| R002 | Ultrastable Encapsulation for 50000 Hours | year_plausibility | 年份 2027 超出 1500–2026 合理区间（晚于当前年份或为远古值） |
| R002 | Ultrastable Encapsulation for 50000 Hours | field_conflict | 类型为 journal_article 但刊名、卷、期、页全部缺失… |
| R002 | Ultrastable Encapsulation for 50000 Hours | doi_syntax | DOI '10.1/short' 不符合注册规则 10.\d{4,9}/… |
```

> 以上输出形态为示例：真实数值以 verify_engine.py 实际运行为准。
