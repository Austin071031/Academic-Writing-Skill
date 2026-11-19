# worked_example.md — 端到端示例（合成示例，非正式案例结果）

> 本文档中的稿件、文献库、判断与输出全部为**合成示例**（SYNTH-01），仅用于演示流程与产物形态。

## 1. 输入（合成）

`task.md`："按 GB/T 7714-2015 顺序编码制整理引用，保持事实一致。"

`manuscript.md`（注意：4 个论断句在同一段里，旧标记 `[1] [2,3] [4] [3-5]` 与文献库映射不可考，
且段末 `[3-5]` 距段尾仅 1 字符，属"段末堆放"观察对象）：

```markdown
# 锂离子电池硅基负极研究进展

硅基负极的理论比容量高达 4200 mAh/g，远超石墨负极的 372 mAh/g [1]。
然而硅在嵌脱锂过程中体积变化超过 300%，导致材料粉化失效 [2,3]。
Chan 等人报道了硅纳米线在循环中保持结构完整 [4]。
这一发现推动了纳米结构硅负极的广泛研究 [3-5]。

## 参考文献

[1] 张三. 硅负极综述[J]. 电化学, 2019, 25(1): 1-10.
```

文献库：`refs.bib`（3 条）+ `refs_ris.ris`（2 条），解析后得 R001–R005。

## 2. 流程

```bash
python3 scripts/init_result.py --case /input/case.json --out /app/output
python3 scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 scripts/parse_manuscript.py /input/manuscript.md --work /app/work
python3 scripts/parse_library.py /input/refs.bib /input/refs_ris.ris --work /app/work
# → 4 段（P001 标题 / P002 正文 / P003 文献表标题 / P004 旧文献条目）；库 5 条
```

## 3. Agent 判断（Phase 3）

按 `claim_rubric.md`，P002 的 4 句均为需引论断（量化事实 ×2、他人结论 ×1、领域共识 ×1），
写 `work/citation_decisions.jsonl`（此处 5 行，第 5 行 C5 是**故意的定位失败演示**）：

```json
{"claim_id": "C1", "pid": "P002", "sentence": "硅基负极的理论比容量高达 4200 mAh/g，远超石墨负极的 372 mAh/g", "claim_type": "quantitative_fact", "entry_ids": ["R001"], "rationale": "量化事实，引权威综述", "position": "after_sentence", "form": "numeric"}
{"claim_id": "C2", "pid": "P002", "sentence": "然而硅在嵌脱锂过程中体积变化超过 300%，导致材料粉化失效", "claim_type": "quantitative_fact", "entry_ids": ["R004", "R005"], "rationale": "一句多引：期刊+会议两条共同支撑", "position": "after_sentence", "form": "numeric"}
{"claim_id": "C3", "pid": "P002", "sentence": "Chan 等人报道了硅纳米线在循环中保持结构完整", "claim_type": "others_result", "entry_ids": ["R003"], "rationale": "他人结论，取最早公开记录", "position": "after_sentence", "form": "numeric"}
{"claim_id": "C4", "pid": "P002", "sentence": "这一发现推动了纳米结构硅负极的广泛研究", "claim_type": "field_consensus", "entry_ids": ["R001", "R002"], "rationale": "共识论断引两篇综述；R001 复用测试多句一引", "position": "after_sentence", "form": "numeric"}
{"claim_id": "C5", "pid": "P002", "sentence": "石墨烯负极的首次报道可追溯至 2004 年", "claim_type": "quantitative_fact", "entry_ids": ["R001"], "rationale": "故意不存在的句子，验证异常路径", "position": "after_sentence", "form": "numeric"}
```

## 4. 引擎执行（Phase 4）

```bash
python3 scripts/place_citations.py --decisions /app/work/citation_decisions.jsonl \
  --manuscript /app/work/manuscript.json --library /app/work/library.json \
  --work /app/work --out /app/output --style gbt2015_numeric --form auto
```

实测输出：

```
[render] 5 条, 样式 gbt2015_numeric -> /app/output/references.md
[place_citations] decisions=5 插入标记=4 文献=5 编号连续=是 异常=1 段末堆放疑似(原稿)=2 插入后错放=0
```

引擎动作分解：
- 剥除旧标记 `[1] [2,3] [4] [3-5]`（记 change_log 4 条中的 remove 项）；
- C5 定位失败 → exceptions.json（`skipped_no_fabrication`），不臆造插入；
- 首次出现顺序：R001→1, R004→2, R005→3, R003→4, R002→5；
- C2 合并为 `[2-3]`；C4 合并为 `[1,5]`（R001 同号复用，审计记 multi_sentence_expansions）。

## 5. 产物（合成示例实测）

`/app/output/edited_manuscript.md`：

```markdown
# 锂离子电池硅基负极研究进展

硅基负极的理论比容量高达 4200 mAh/g，远超石墨负极的 372 mAh/g[1]。 然而硅在嵌脱锂过程中体积变化超过 300%，导致材料粉化失效[2-3]。 Chan 等人报道了硅纳米线在循环中保持结构完整[4]。 这一发现推动了纳米结构硅负极的广泛研究[1,5]。
```

`/app/output/references.md`（按引用顺序，编号 1-5 连续）：

```markdown
## 参考文献

[1] Smith, John, Lee, Ken. Silicon Anodes for Lithium-Ion Batteries: A Review[J]. Nature Energy, 2020, 5(3): 200-210. DOI: 10.1038/s41560-020-0555-5.
[2] Wang, Li, Chen, Hao. Volume Expansion of Silicon Electrodes[J]. J. Electrochem. Soc, 2018, 165(8): A1500-A1508. DOI: 10.1149/2.0341808jes.
[3] Wang, Li, Chen, Hao. 硅电极体积膨胀研究[C]. 全国电化学会议, 2018: 15-20.
[4] Smith, John, Lee, Ken. Silicon Anodes for Lithium-Ion Batteries: A Review[EB], 2019.
[5] Smith, John, Lee, Ken. 锂离子电池硅负极综述[J]. 储能科学与技术, 2020, 9(2): 401-410.
```

`placement_audit.json` 摘要：原稿段末堆放疑似 2 处（`[4]` 距段尾 28 字符、`[3-5]` 距段尾 1 字符）；
插入后错放 0 处；一句多引合并 2 组均单标记无相邻括号；多句一引展开 R001→编号 1、2 处引用位点。

## 6. 收尾（Phase 5）

```bash
python3 scripts/assemble_result.py --work /app/work --out /app/output --case /input/case.json --skill "citation-placement-skill v1.0.0" --status success
python3 scripts/validate_output.py --out /app/output --work /app/work --expect-status success
# [validate] PASS (status=success)
python3 scripts/render_previews.py --out /app/output --work /app/work
```
