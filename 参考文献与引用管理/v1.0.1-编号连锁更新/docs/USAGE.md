# USAGE｜编号连锁更新完整调用步骤

> 安装方式：本目录 = `/skills/weekly-skill`。以下命令全部可在沙箱内按字面执行。

## 0. 输入契约

| 输入 | 位置 | 说明 |
|---|---|---|
| case.json / task.md | /input/ | 任务书；Agent 从这里识别编辑操作 |
| 稿件 | /input/*.md/txt/tex/docx/pdf | parse_manuscript 支持 5 种格式 |
| 文献库 | /input/*.bib/ris/enw/ciw/nbib/txt/csv/json | parse_library 支持 8 种格式 |

## 1. 标准流水线（逐字命令）

```bash
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_manuscript.py "$(ls /input/*.md /input/*.txt /input/*.tex 2>/dev/null | head -1)" --work /app/work
python3 $S/parse_library.py /input/*.bib /input/*.ris /input/*.enw /input/*.ciw /input/*.nbib /input/*.csv 2>/dev/null --work /app/work || \
python3 $S/parse_library.py /input/*.json --work /app/work || true
```

若稿件自带文末列表而 parse 未覆盖（列表条目无 `[n]` 前缀等），Agent 手工写：

```bash
cat > /app/work/reference_list.json <<'EOF'
[{"num": 1, "text": "张三. 正极材料基础[J]. 电池科学, 2019, 10(2): 12-20."}]
EOF
```

写编辑操作并跑引擎：

```bash
cat > /app/work/edit_ops.json <<'EOF'
[{"op": "delete", "ref_id": "R004", "note": "任务书：删除该专著条目"},
 {"op": "reorder", "ref_ids": ["R002", "R001"], "note": "任务书：R002 提前"}]
EOF
python3 $S/renumber_plan.py --work /app/work --out /app/output --engine $S/cite_engine.py
```

判读（关键三步）：

1. stdout 末行 `INVARIANTS: PASS/FAIL` —— 终检唯一权威结论；
2. `/app/output/renumber_report.md` —— 操作清单 → 映射表 → 悬空清单 → 终检结论；
3. 若 FAIL 且悬空清单非空：打开 `work/manuscript.json`，对清单中 pid 的段落改写句子
   （删引/改引存活条目/补新引 `[库编号]`），**不要改数字**，然后重跑引擎命令。

收尾：

```bash
python3 $S/cite_engine.py audit --manuscript /app/work/manuscript.renumbered.json --nrefs <invariants.list_entries>
python3 $S/assemble_result.py --work /app/work --out /app/output --skill "citation-renumber-chain v2.0.0" --status success
python3 $S/validate_output.py --out /app/output --expect-status success   # 必须 exit 0
python3 $S/render_previews.py --out /app/output                            # preview.html 必出
```

## 2. 输入输出一览

| 文件 | 方向 | 内容 |
|---|---|---|
| work/edit_ops.json | Agent 写 | [{op, ref_id/from/to/ref_ids/keep, note}] |
| work/manuscript.json, work/library.json | 脚本产 | 解析结果 |
| work/mapping.json | 引擎产 | 旧号→新号（null=删除） |
| work/manuscript.renumbered.json | 引擎产 | 连锁重排后全文（含各 kind 段 cite_marks 更新） |
| work/library_reordered.json | 引擎产 | 按新序存活记录（含 source_file/source_index） |
| /app/output/edited_manuscript.md | 引擎产 | 可编辑交付稿（旧列表段已替换为重建列表） |
| /app/output/references.md, references.json | 引擎产 | 重建文末列表；json 每条含 number/id/text/source_file/source_index |
| /app/output/renumber_report.md | 引擎产 | 人读报告 |
| work/renumber_report.json | 引擎产 | 机读报告（mapping/deleted/dangling_refs/invariants/PASS） |

## 3. 自查方法

- `python3 -c "import json;r=json.load(open('/app/work/renumber_report.json'));print(r['PASS'],r['invariants'])"`
- 连续性独立复核：`work/renumber_report.json → invariants` 应与
  `work/consistency_audit.json` 一致（引擎为准）。
- `references.json` 的 number 必须等于 1..len(entries)（validate_output 也会复检）。

## 4. 附录：合成案例端到端实测记录（2026-11-19，沙箱实测）

合成输入：6 条文献库（bibtex）+ 含正文/图注/表注/附录/脚注/文末列表的稿件，
引用含区间 `[1-3]`、一句多引 `[2,5,6]`。

**场景A（删除 1 条 + 调换 2 条顺序 → PASS）**

edit_ops：`[{"op":"delete","ref_id":"R004"},{"op":"reorder","ref_ids":["R002","R001"]}]`

```
$ python3 scripts/renumber_plan.py --work work --out output --engine scripts/cite_engine.py
[renumber_plan] 映射 5 条, 删除 1 条, 悬空段落 0 处
INVARIANTS: PASS            # exit 0
```

mapping：`{1:2, 2:1, 3:3, 4:null, 5:4, 6:5}`；正文 `[2,5,6]→[1,4-5]`（区间压缩）、
图注 `[3,5]→[3-4]`、脚注 `[2]→[1]` 全部同步；references.md 5 条按新序。

收尾：
```
[assemble] status=success outputs=['edited_manuscript','references','renumber_report']
[validate] PASS (status=success)     # exit 0
[render_previews] preview.html 已生成
```

**场景B（删除仍被引用的条目 → 引擎正确报告悬空，FAIL）**

edit_ops：`[{"op":"delete","ref_id":"3"}]`（不修复任何句子）：

```
[renumber_plan] 映射 5 条, 删除 1 条, 悬空段落 2 处
INVARIANTS: FAIL            # exit 1
悬空: P002 body [1-3] 涉及旧号 [3]；P004 figure_note [3,5] 涉及旧号 [3]
```

**其他已实测分支**：merge（`keep R005, drop R006`，删除后 keep 按条目身份正确定位）；
insert_existing（库 7 条/手工列表 6 条时从库中拉入 R007，并支持正文直接引用其库编号
`[7]→[2]`）；著者-出版年模式（不重排，报告 `list_sorted_by_first_author` 与 stale 清单）。
