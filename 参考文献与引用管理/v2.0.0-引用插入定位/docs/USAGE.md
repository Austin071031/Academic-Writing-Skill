# USAGE.md — 完整调用步骤、输入输出与自查方法

## 1. 安装

整个版本目录即 Skill 本体，评测时安装为 `/skills/weekly-skill`。
仅依赖 Python 3 标准库，无网络需求。`scripts/` 含共享核心 8 脚本（接口与 SPEC-common 一致）
与专属脚本 `place_citations.py`。

## 2. 输入

| 输入 | 位置 | 说明 |
|---|---|---|
| case.json | /input/case.json | 含 case_id 与 output_contract |
| task.md | /input/task.md | 任务书；引用形式（顺序编码制/著者-出版年）以此为准 |
| 稿件 | /input/ 下 | md/txt/tex/docx/pdf，由 parse_manuscript.py 分段 |
| 文献库 | /input/ 下 | bib/ris/enw/ciw/csv/json/GB-T 文本，可多文件 |

## 3. 调用步骤（逐字命令）

```bash
# Phase 0 骨架
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
# Phase 1 侦查
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 /skills/weekly-skill/scripts/parse_manuscript.py /input/<稿件> --work /app/work
python3 /skills/weekly-skill/scripts/parse_library.py /input/<库1> [/input/<库2>] --work /app/work
# Phase 3（Agent 写 work/citation_decisions.jsonl，每行一条，见 SKILL.md）
# Phase 4 引擎
python3 /skills/weekly-skill/scripts/place_citations.py \
  --decisions /app/work/citation_decisions.jsonl \
  --manuscript /app/work/manuscript.json \
  --library /app/work/library.json \
  --work /app/work --out /app/output \
  --style gbt2015_numeric --form auto
# 可选一致性复检
python3 /skills/weekly-skill/scripts/cite_engine.py audit \
  --manuscript /app/work/manuscript.placed.json --nrefs <库条目数>
# Phase 5 汇总
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output \
  --case /input/case.json --skill "citation-placement-skill v1.0.0" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --work /app/work --expect-status success
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output --work /app/work
```

## 4. place_citations.py 参数与产物

参数：`--decisions --manuscript --library --work --out --style --form [--keep-existing] [--keep-old-refs]`

产物：
- `/app/output/edited_manuscript.md` — 插入引用后的全文（保留段落结构与标题；旧文献表段落默认移除）
- `/app/output/references.md` + `references.json` — 按引用顺序的参考文献表
- `/app/output/placement_audit.json` — 错放审计（work/ 下同名副本）
- `work/exceptions.json / change_log.json / evidence_map.json / stats.json / citation_order.json / manuscript.placed.json`

decisions 每行字段：`claim_id, pid, sentence, claim_type, entry_ids[], rationale,
position(after_sentence|before_sentence), form(numeric|author_year)`。sentence 必须逐字取自
manuscript.json 对应段落 text；定位失败记 exceptions 并跳过。

## 5. 自查方法（合成案例实测记录）

> 以下为本 Skill 开发时的真实自测记录。说明：/tmp/tc 是多版本并行开发共用目录、
> 输入会被并发改写，故自测在隔离副本 /tmp/tc-v1 进行，输入文件与 /tmp/tc/input 的
> SYNTH-01 合成案例逐字节一致（md5 相同）。

```bash
S=/skills/weekly-skill/scripts   # 自测时替换为本地 scripts 路径
python3 $S/init_result.py --case /tmp/tc-v1/input/case.json --out /tmp/tc-v1/output
python3 $S/inspect_case.py --case /tmp/tc-v1/input/case.json --task /tmp/tc-v1/input/task.md --input-dir /tmp/tc-v1/input --work /tmp/tc-v1/work
python3 $S/parse_manuscript.py /tmp/tc-v1/input/manuscript.md --work /tmp/tc-v1/work
python3 $S/parse_library.py /tmp/tc-v1/input/refs.bib /tmp/tc-v1/input/refs_ris.ris --work /tmp/tc-v1/work
# 手写 5 条 decisions（含 1 条故意定位失败）至 /tmp/tc-v1/work/citation_decisions.jsonl
python3 $S/place_citations.py --decisions /tmp/tc-v1/work/citation_decisions.jsonl \
  --manuscript /tmp/tc-v1/work/manuscript.json --library /tmp/tc-v1/work/library.json \
  --work /tmp/tc-v1/work --out /tmp/tc-v1/output --style gbt2015_numeric --form auto
python3 $S/assemble_result.py --work /tmp/tc-v1/work --out /tmp/tc-v1/output \
  --case /tmp/tc-v1/input/case.json --skill "citation-placement-skill v1.0.0" --status success
python3 $S/validate_output.py --out /tmp/tc-v1/output --work /tmp/tc-v1/work --expect-status success
python3 $S/render_previews.py --out /tmp/tc-v1/output --work /tmp/tc-v1/work
```

实测输出摘要（exit 码全为 0）：

```
[init_result] 骨架已写入 /tmp/tc-v1/output/result.json (case_id=SYNTH-01)
[inspect_case] case_id=SYNTH-01 材料=5 稿件候选=1 文献库候选=2 样式=numeric
[parse_manuscript] 4 段, 5 个引用标记, 样式=['numeric']
[parse_library] 共 5 条 -> /tmp/tc-v1/work/library.json
[render] 5 条, 样式 gbt2015_numeric -> /tmp/tc-v1/output/references.md
[place_citations] decisions=5 插入标记=4 文献=5 编号连续=是 异常=1 段末堆放疑似(原稿)=2 插入后错放=0
[assemble] status=success outputs=['edited_manuscript', 'references'] -> /tmp/tc-v1/output/result.json
[validate] PASS (status=success)
[render_previews] preview.html 已生成
```

逐项核验清单：
1. `edited_manuscript.md` 中 4 个标记均在各自论断句末、句号之前：`[1]` `[2-3]` `[4]` `[1,5]`。
2. `references.json` 编号 `[1,2,3,4,5]` 连续；顺序 = 首次出现顺序 R001,R004,R005,R003,R002。
3. `placement_audit.json`：原稿段末堆放疑似 2 处（`[4]` 距段尾 28 字符、`[3-5]` 距段尾 1 字符）；
   插入后错放 0；一句多引 2 组均单标记无 `][`；多句一引 R001 展开为 2 处同号标记。
4. `exceptions.json` 恰 1 条（C5 定位失败，`skipped_no_fabrication`），未臆造插入。
5. `result.json` 含 case_id、status=success、output_contract 四字段（result/evidence/changes/status）均已回填。
6. `validate_output.py` 打印 PASS 且 exit 0；`preview.html` 已生成。

## 6. 边界与限制

- sentence 定位依赖"逐字子串"（三级容错：精确/空白宽容/去空白）；Agent 改写过的句子无法定位，会进 exceptions。
- 旧引用标记默认剥除重放（旧编号与库映射不可考）；需保留现有编号体系时用 `--keep-existing`，
  但新插入条目编号将排在已有最大编号之后，全文连续性需人工确认。
- author_year 形式按段落是否含 CJK 自动选全/半角括号；文献表在 author_year 模式下仍按引用顺序输出。
- 图表题注、脚注等非 body 段落不接受插入（引擎拒绝并记 exception）。
