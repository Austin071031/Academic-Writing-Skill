# Worked Example（/tmp/tc/input 合成案例，端到端）

> 合成案例（非真实评审数据）：`/tmp/tc/input` 含 `case.json`、`task.md`、`refs.bib`、`refs_ris.ris`、`manuscript.md`。
> 任务书："按 GB/T 7714-2015 顺序编码制整理引用" → 风格判定 `gbt2015_numeric`。

## 输入概况

- `refs.bib`：3 条 BibTeX —— 英文期刊（R001，字段全）、中文期刊（R002，缺 DOI）、英文预印本（R003，misc，缺卷/期/页/DOI，年份 2019）。
- `refs_ris.ris`：2 条 RIS —— 英文期刊（R004，字段全）、中文会议（R005，缺卷/期/DOI）。

## 逐步命令（自测等价物，正式环境用 /skills/weekly-skill 绝对路径）

```bash
cd /tmp/tc
python3 scripts/init_result.py --case input/case.json --out output
python3 scripts/inspect_case.py --case input/case.json --task input/task.md --input-dir input --work work
python3 scripts/parse_library.py input/refs.bib input/refs_ris.ris --work work
python3 scripts/convert_engine.py --library work/library.json --to gbt2015_numeric \
    --outdir output --work work --specs-dir <SKILL_DIR>/references/format_specs --try-online
python3 scripts/assemble_result.py --work work --out output --case input/case.json \
    --skill "ref-format-converter v4.0.0" --status success
python3 scripts/validate_output.py --out output
python3 scripts/render_previews.py --out output
```

## 预期结果（合成数据上的真实行为）

- `output/converted_refs.txt` / `references.md`：5 条 GB/T 顺序编码条目；R002 中文条目全角标点；
  R001/R004 英文条目半角；`Smith, John` → `Smith J`；DOI 原样保留。
- `output/field_audit.json`：
  - R002 `missing_fields=["doi"]`，action `not_provided`（"材料未提供，不得臆造补齐"）；
  - R003 `missing_fields=["volume","issue","pages","doi"]`，全部 `not_provided`
    （与 R001 同题但年份 2019≠2020 且类型 misc≠journal_article，**不允许**跨条目互补，防止把预印本升级成期刊）；
  - R005 `missing_fields=["volume","issue","doi"]`，`not_provided`。
- `--try-online` 在无网络沙箱中 5 秒超时失败，exceptions.json 记录 `Crossref 探测失败`，
  审计中 DOI 项标 `unverified`。
- `convert_report.md`：源格式统计（bibtex×3, ris×2）→ 逐条前后对照 → 字段保留率 → 未提供字段清单。
- `validate_output.py` 输出 PASS。

## 跨条目互补的正例（另见 evaluation/test_texts.md）

两条同题、同年、同类型的重复条目（一条有 DOI 一条没有）会被互补：
动作记为 `copied_from_R00X`，`source_rid` 指向供体条目，change_log 同步记录。
