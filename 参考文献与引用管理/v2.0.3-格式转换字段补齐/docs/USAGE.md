# USAGE — v1.0.3｜格式转换与字段补齐（ref-format-converter v4.0.0）

## 1. 完整调用步骤

设 `SKILL_DIR=/skills/weekly-skill`（本地自测即本目录）。

```bash
# Phase 0：骨架 + 案件解析
python3 $SKILL_DIR/scripts/init_result.py --case /input/case.json --out /app/output
python3 $SKILL_DIR/scripts/inspect_case.py --case /input/case.json --task /input/task.md \
    --input-dir /input --work /app/work
# Phase 1：解析文献库（文件清单抄自 work/inspection.json 的 library_candidates）
python3 $SKILL_DIR/scripts/parse_library.py /input/refs.bib /input/refs.ris --work /app/work
# Phase 2：Agent 判定目标规范（规则见 SKILL.md：GB/T→gbt2015_numeric；著者-出版年→gbt2015_author；
#          APA→apa7；Vancouver/IEEE→vancouver；导出回转→bibtex/ris）
# Phase 3：转换 + 字段审计
python3 $SKILL_DIR/scripts/convert_engine.py --library /app/work/library.json \
    --to gbt2015_numeric --outdir /app/output --work /app/work \
    --specs-dir $SKILL_DIR/references/format_specs --try-online
# Phase 4：Agent 审查 field_audit.json / convert_report.md，登记 uncertainty/manual_confirmations
# Phase 5：固定收尾
python3 $SKILL_DIR/scripts/assemble_result.py --work /app/work --out /app/output \
    --case /input/case.json --skill "ref-format-converter v4.0.0" --status success
python3 $SKILL_DIR/scripts/validate_output.py --out /app/output
python3 $SKILL_DIR/scripts/render_previews.py --out /app/output
```

## 2. 输入 / 输出

输入：`/input/case.json`、`/input/task.md`、文献库文件（bib/ris/enw/ciw/csv/json/CNKI 文本）。
convert_engine 直接消费 `work/library.json`。

输出（/app/output）：

| 文件 | 内容 |
|---|---|
| converted_refs.txt | 目标格式条目全文（GB/T 带 [n] 编号；bibtex/ris 为导出文本） |
| references.md / references.json | 同内容的 md 与结构化版本（bibtex/ris 时 md 为代码块包装） |
| field_audit.json | 逐条 `{rid, missing_fields, fills[{field, action, source_rid, note}], fields_kept...}` |
| convert_report.md / report.md | 人读报告：源格式统计→前后对照→字段保留率→未提供清单→互补记录 |
| result.json / preview.html | 汇总契约结果与预览 |

## 3. 实测记录（2026-11-19，本目录代码真实运行）

### 3.1 端到端（/tmp/tc/input 快照，10 条 bibtex 含中文条目与空缺字段）

```
[init_result] 骨架已写入 (case_id=SYNTH-V5)
[inspect_case] 材料=5 文献库候选=2 样式=numeric
[parse_library] refs.bib: 4 条; library.bib: 6 条; 共 10 条
[convert_engine] 10 条 -> gbt2015_numeric; 保留率 100.0%; 缺字段实例 14; 互补补齐 0; online=reachable
[assemble] status=success outputs=['references', 'report', 'converted_refs']
[validate] PASS (status=success)   exit=0
[render_previews] preview.html 已生成
```

抽查：含空字段的条目（journal/volume/pages 为空）被正确列出
`missing_fields=[venue,volume,issue,pages]` 且全部 `not_provided`；
中文条目输出全角（`张三．正极材料基础[J]．电池科学，2019，10（2）：12-20．`）。

### 3.2 六种目标各跑一次（合成中英混排库 5 条：含 4 作者、缺页码、会议、同题重复对）

| --to | 结果行（摘录） | 保留率 |
|---|---|---|
| gbt2015_numeric | `[1] Smith J, Lee K, Brown A, et al. ...[J]. Nature Energy, 2020, 5(3): 200-210. DOI: ...`；中文条目全角 | 100% |
| gbt2015_author | 同上（不编号） | 100% |
| apa7 | `Smith, J., Lee, K., Brown, A., Clark, Z. (2020). ... *Nature Energy*, *5*(3), 200-210. https://doi.org/...`；中文条目半角 | 100% |
| vancouver | `[1] Smith J, ... Nature Energy. 2020;5(3):200-210. doi:...` | 100% |
| bibtex | `@article{R001, ... doi = {10.1038/...}}` 字段逐一回写 | 100% |
| ris | `TY  - JOUR / AU  - ... / DO  - ... / ER  -` | 100% |

同题重复对（R004/R005）：R005 的 volume/pages/doi 被互补，审计记
`copied_from_R004`（source_rid=R004）；`issue` 双方均缺 → `not_provided`。

### 3.3 离线降级实测（强制代理指向 127.0.0.1:9 模拟无网络）

```
online=unavailable: URLError: <urlopen error [Errno 111] Connection refused>
exceptions.json: Crossref 探测失败（5s 超时）→ 缺失 DOI 一律 unverified/not_provided
field_audit R002.doi: "材料未提供，不得臆造补齐；Crossref 探测失败，状态 unverified"
```

## 4. 自查方法

1. `python3 $SKILL_DIR/scripts/validate_output.py --out /app/output` 必须 PASS。
2. `jq '.summary' /app/output/field_audit.json`：`field_retention_rate ≥ 0.95`；
   `n_not_provided` 与 convert_report 第 4 节行数一致。
3. 抽查任一中文条目标点为全角、任一英文条目为半角；DOI 串与原材料逐字符一致。
4. 若发现"缺失字段却出现在最终条目"→ 触发诚实红线，返工（见 evaluation/scoring_sheet.md）。

## 5. 已知限制（诚实声明）

- `gbt2015_author` 的条目本体与顺序编码一致、仅去掉 [n] 编号；著者-出版年制的
  "年份前移"与字顺排序需以 order.json 与人工排序补足（共享内核 render 的既有行为）。
- Vancouver/APA 的作者截断遵循共享内核（≤3 + et al），与 ICMJE ≤6 的差异已在
  format_specs/vancouver.md 注明；完整作者名单始终保留在 library.json。
- 中文条目内小数点（如 v3.2）会被全角化，发现后列入 manual_confirmations。
- 页码缩写（200-210→200-10）、刊名 NLM 缩写不做（需外部词表，照录原值）。
- 联网补齐仅探测不自动写值；可达时转 manual_confirmations 由人核对。
