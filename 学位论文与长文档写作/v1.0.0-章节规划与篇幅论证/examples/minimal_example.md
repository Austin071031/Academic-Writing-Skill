# 最小调用示例（示例，非正式案例结果）

## 输入（合成）
- `case.json`: {"case_id":"demo", "output_contract":{"result":"…","main_document":"…","evidence_map":"…","change_log":"…","uncertainty":"…","stats":"…"}}
- `task.md`: "依据大纲与材料撰写第3章结果与讨论草稿"
- `outline.md`: 含「第3章 结果与讨论（约4000字）」及要素行
- 材料：`ch1_intro.md`、`ch2_method.md`、`facts.md`（含 5.8 mS/cm 等记录）、`refs.bib`

## 调用
按 SKILL.md Phase 0-5 执行；关键一步：

```bash
python3 scripts/outline_engine.py check --chapter work/draft_ch3.md \
  --chapters work/chapters.json --plan work/chapter_plan.json \
  --materials work/materials_all.txt --work work
```

## 示意输出（示例，非正式案例结果）

```
[outline_engine check] 2450 字，偏差 -0.06，要素缺失 []，数值未溯源 0
```
`chapter_check.json` 中 `numbers` 含：
`{"raw":"81%","status":"derived","derivation":"(5.8-3.2)/3.2=0.8125≈0.81"}`

`result.json` 示例（节选）：
```json
{"case_id":"demo","status":"success","skill":"longdoc-chapter-planning v1.0.0",
 "outputs":{"chapter_plan":"chapter_plan.md","coverage_report":"coverage_report.md","chapter_3":"chapter_3.md"}}
```
