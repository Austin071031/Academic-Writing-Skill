# 输出契约与文件格式规范（output spec）

## /app/output 产物清单

| 文件 | 生成者 | 格式要点 |
|-|-|-|
| `result.json` | init_result → assemble → validate | 见下节 |
| `polished_full.md` | assemble | 章节层级、公式、引用、图表编号与源稿一致；可直接粘回 |
| `change_log.jsonl` / `.md` | assemble | 逐句记录；modify 句必有 types+reason |
| `sentence_alignment.md` | assemble（--bilingual） | 逐句 原文/改文/类型/理由 表 |
| `terminology_table.md` / `.csv` | assemble | 复自 work/term_table.csv |
| `review_report.md` | assemble | 一致性回扫 + 守恒检查 + resolutions 处置 |
| `diff.html`、`polished_full.html` | assemble | 自包含 HTML，浏览器直接打开 |
| `preview_polished.pdf/.png` | render_previews | 有 CJK 字体时生成；否则仅在 preview_report.json 说明 |

## change_log.jsonl 行结构

```json
{"id": "doc-B3-P1-S2", "original": "源句原文", "polished": "改后句子",
 "decision": "modify | keep", "types": ["grammar"],
 "reason": "一句话理由（≤40字）", "logged": true}
```

- `id` 与 source_dump.md 完全一致（句级 ID：`-S{n}` 后缀；单句块用块 ID）。
- `types` 取值受控：grammar/syntax/collocation/punctuation/spelling/long-sentence/
  terminology/abbreviation/register/redundancy/logic/clarity/hedging/formatting/other。
- `keep` 句的 reason 写明保留依据；"存疑"句 reason 以"存疑："开头并进入人工确认清单。

## result.json 结构

```json
{
  "case_id": "<原 case_id>",
  "status": "complete | partial | failed | in_progress",
  "output_contract": {
    "<原契约键>": {"spec": "<原契约描述>", "delivered": "<产物文件>",
                   "artifact_path": "<绝对路径>", "null_reason": "<无法交付时必填>"}
  },
  "artifacts": {"polished_full": "polished_full.md", ...},
  "change_records": {"change_log_jsonl": "...", "change_log_md": "...",
                     "summary": {"sentences_total": N, "modified": N, "kept": N,
                                 "unlogged": N, "by_type": {...}}},
  "fact_preservation": {"guard_report": "review_report.md",
                        "critical_unresolved": 0, "coverage_ratio": 1.0},
  "sources": ["输入材料相对路径"],
  "assumptions": [], "uncertainty": [], "manual_review_required": [],
  "runtime": {"model_requests_used": null, "notes": "..."}
}
```

规则：
- `output_contract` 必须覆盖 case.json 中的全部键；交付填 `delivered`+`artifact_path`，
  无法交付填 `null_reason`（不许静默为空）。
- `status` 由 validate_output.py 判定：产物齐、契约闭环、critical=0、覆盖率 100% → complete；
  有未完成项但能交付部分产物 → partial；无有效产物 → failed。
- 材料缺口、编码异常、术语冲突、未提取文件一律进 `uncertainty` 或 `manual_review_required`。
