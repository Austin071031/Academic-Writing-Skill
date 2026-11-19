# 使用说明（USAGE）

## 输入与输出

- 输入：`/input/case.json`、`/input/task.md`、分章节稿件（md/txt/tex/docx/pdf）、
  事实材料、（可选）文献库与组织方工单。
- 中间产物（`/app/work`）：
  `inspection.json`（输入清单）、`chapters.json`（分章段落）、
  `glossary_candidates.json`（术语候选三类）、`glossary_review.json`（Agent 审定）、
  `glossary.md`（术语表）、`consistency_report.{json,md}`（异写与符号冲突）、
  `xref_audit.json`（交叉引用审计）、`contradiction_candidates.json`（矛盾候选）、
  `impact_report.{json,md}`（影响面）、`evidence_map.json` / `change_log.json` /
  `uncertainty.json` / `manual_confirmations.json` / `exceptions.json` / `stats.json`。
- 交付（`/app/output`）：`glossary.md`、`consistency_report.md`、`impact_report.md`、
  （若有改稿）`revised_*.md`、`result.json`（含 output_contract 全部字段）、
  `preview.html`。

## glossary_review.json 格式（Agent 审定后手写）

```json
[
  {"canonical": "固态电解质",
   "variants": ["SSE", "solid-state electrolyte"],
   "definition_pid": "C01-S001-P001",
   "keep": true},
  {"canonical": "两步烧结", "variants": ["两步烧结法"], "definition_pid": null, "keep": true},
  {"canonical": "本文研究", "variants": [], "definition_pid": null, "keep": false}
]
```
- `canonical`：全文统一使用的规范写法（必填，非空）；有定义处优先取定义处写法。
- `variants`：认可出现过的全部写法（缩写、英文全称、历史异写），引擎按它逐处核查。
- `definition_pid`：定义出现段落 pid；无定义（高频词类）填 null——红线 1 禁止编造。
- `keep=false`：剔除伪术语候选。

## 完整调用序列（参考）

```bash
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_chapters.py $(ls /input/chapters/*.md /input/materials/*.md) --work /app/work
python3 $S/consistency_engine.py scan --chapters /app/work/chapters.json --work /app/work
# Agent 审定 → 写 /app/work/glossary_review.json；裁决矛盾候选；处理 dangling
python3 $S/consistency_engine.py glossary --chapters /app/work/chapters.json \
  --review /app/work/glossary_review.json --work /app/work
# （可选）改稿后复核：重新 parse_chapters + scan + glossary
python3 $S/consistency_engine.py impact --chapters /app/work/chapters.json \
  --glossary /app/work/glossary.md --changed-term "固态电解质" --work /app/work
cp /app/work/glossary.md /app/work/consistency_report.md /app/work/impact_report.md /app/output/
python3 $S/assemble_result.py --work /app/work --out /app/output \
  --skill "longdoc-consistency v1.0.1" --status success
python3 $S/validate_output.py --out /app/output --work /app/work
python3 $S/render_previews.py --out /app/output
```

## 自查方法（评分前自检）

1. `validate_output.py --out /app/output --work /app/work` 必须 PASS
   （xref_audit.json dangling 非空时必 FAIL——修复或降级，禁止删审计文件）。
2. `result.json` 中 output_contract 声明的字段全部存在；status 与实际相符；
   status=success 时 evidence_map 非空。
3. `consistency_report.json`：异写逐处有 pid+原文；改稿后复跑异写数=0 或残留均有
   manual_confirmations 理由。
4. `contradiction_candidates.json` 每对都有裁决记录（change_log 或
   manual_confirmations）。
5. `glossary.md` 每条 canonical 的 variants 与原文实际写法对得上（抽查 3 条）。
6. `impact_report` 的 pid 清单抽查 2 条：确实引用该术语/指向该章。

## 篇幅与规模上限

- 单文件读取与段落解析同 parse_chapters（inspect 截断 200 KB；parse_chapters 全量，
  单稿 >5 MB 建议分文件调用并记 exceptions）。
- 术语候选每类上限 60 条；异写清单每术语在 .md 中最多列 50 处（.json 全量）。
- 结论句两两比对约 200 万次集合运算内为秒级；结论句 >2000 句建议分批并记 stats。
- 目录交付约束：Skill 目录总文件 ≤50、总大小 ≤2 MB、无符号链接。
