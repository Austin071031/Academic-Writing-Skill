# 完整调用说明

## 输入

| 文件 | 说明 |
|-|-|
| /input/case.json | 案例标识与 output_contract |
| /input/task.md | 任务说明：目标受众、文体、篇幅约束 |
| /input/其他材料 | 源文（md/txt/tex/pdf/docx）、事实底稿、数据表 |

## 调用步骤

1. `init_result.py` 落盘骨架 result.json。
2. `inspect_case.py` 解析出受众/文体/篇幅/源文候选 → work/inspection.json。
3. `parse_source.py <源文>` → work/source.json（段落 pid、事实清单）。
4. `claim_engine.py extract --source work/source.json` → work/source_claims.json
   （论断句清单：强度级别 L0-L3、因果性、否定极性、标记）。
5. Agent 按论断清单撰写 work/rewrite_draft.md（强度/因果/否定/限定条件与源文同级）。
6. `align_rewrite.py` → work/alignment.json；`claim_engine.py check --rewrite work/rewrite_draft.md`
   → work/claim_report.json + claim_report.md + claim_verdicts.jsonl（exit=0 才达标）。
7. critical（upgraded/absolute_upgrade/causality_upgrade/negation_flip/new_claim）逐条修复并重跑 check 至 exit=0。
8. Agent 写 evidence_map/change_log/uncertainty/manual_confirmations。
9. 复制 rewrite.md 与 claim_report.md 到 /app/output，`assemble_result.py` → `validate_output.py` → `render_previews.py`。

## 输出

| 文件 | 说明 |
|-|-|
| rewrite.md | 可编辑改写稿（主产物） |
| claim_report.md | 论断强度校准报告（人读，含逐条判定与修改建议） |
| result.json | case_id、status、output_contract 字段、产物清单、内嵌台账 |
| preview.html | 全部 md 产物的渲染预览 |
| work/source_claims.json / claim_verdicts.jsonl | 源文论断清单与逐条判定（机读） |

## 判定口径（详见 references/claim_rules.md）

- kept：强度同级；downgraded：更保守（info，允许）；
- upgraded / absolute_upgrade / causality_upgrade / negation_flip / new_claim：critical，必须修复；
- missing：关键论断丢失（warn，补回或写明删除理由）。

## 自查方法

- `claim_engine.py check` exit=0 且无 critical；
- alignment 无"非故意" dropped；关键论断无 missing；
- evidence_map 覆盖全部数据点与关键论断；status 与实际完成度一致。

## 限制

- 强度/因果标记为词表启发式：未列出的 hedging 措辞（如"一定程度上"）不识别；
  否定词属于句中其他成分（如"未包覆"）时极性判断可能失误，需人工复核。
- 句级对齐为 2-gram Dice 启发式，大改写可能漏配（判 missing/new_claim 时先人工确认再改稿）。
- 引擎只比对强度与论据边界；数据/单位逐值核验见 transfer-fact-fidelity 版本。
