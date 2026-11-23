# 最小调用示例（示意输出标注为示例，非正式案例结果）

## 输入

`/input/case.json`：`{"case_id":"demo-ec","output_contract":{"annotated_manuscript":"批注版手稿","polished_text":"采纳版全文","edit_cards":"编辑卡","acceptance_checklist":"验收清单"}}`
`/input/task.md`：润色摘要，拿不准的地方标出来，我要逐条接受或拒绝。
`/input/abs.md`：

```markdown
## 摘要
我们做了一个新的方法，可以大幅提高预测精度。实验结果显示，误差降低了约15%[1]。结果证明该方法是国际领先的。
```

## 调用

```bash
python3 /skills/weekly-skill/scripts/segment_util.py --input-dir /input --work-dir /app/work --output-dir /app/output
# Agent：阶段2 诊断 + 阶段3 处方分级 → edit_records/chunk_001.jsonl
python3 /skills/weekly-skill/scripts/annotate.py --work-dir /app/work --output-dir /app/output
python3 /skills/weekly-skill/scripts/terminology.py build --segments /app/work/source_segments.json --out /app/work
python3 /skills/weekly-skill/scripts/validate_output.py --work-dir /app/work --output-dir /app/output
```

## 示意 edit_records 行（示例）

```json
{"id":"abs-B2-P1-S1","original":"我们做了一个新的方法，可以大幅提高预测精度。","action":"apply","diagnosis":"口语化（做了/大幅）+人称主语","prescription":"本文提出一种新方法，可显著提高预测精度。","reason":"“做了”改书面语“提出”；去人称主语；限定词“大幅→显著”同档","types":["register","collocation"],"confidence":"high","note":""}
{"id":"abs-B2-P1-S3","original":"结果证明该方法是国际领先的。","action":"confirm","diagnosis":"强断言（证明）+无证据最高级（国际领先）","prescription":"结果表明该方法具有竞争力。","reason":"证据强度不足以支撑强档断言；但降级改变作者主张，需作者裁决","types":["hedging","register"],"confidence":"low","note":"若作者能提供对比实验证据，可保留更强表述"}
```

## 示意 annotated_manuscript.md（示例）

```markdown
## 摘要
[E1]~~我们做了一个新的方法，可以大幅提高预测精度。~~ → **本文提出一种新方法，可显著提高预测精度。**[/E1] 实验结果显示，误差降低了约15%[1]。 [E2]结果证明该方法是国际领先的。[/E2]〔待确认：强断言+无证据最高级〕
```
