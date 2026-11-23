# 最小调用示例（示意输出标注为示例，非正式案例结果）

## 输入

`/input/case.json`：`{"case_id":"demo-bt","output_contract":{"polished_text":"x","change_log":"y"}}`
`/input/task.md`：润色以下英文摘要为期刊风格，不得改动数值与结论强度。
`/input/abstract.md`：

```markdown
## Abstract
The results of our experiments shows that the new catalyst can achieve a activity of 98.5%, which is much better than reported catalysts [2]. This definitely proves the mechanism.
```

## 调用

```bash
python3 /skills/weekly-skill/scripts/segment_util.py --input-dir /input --work-dir /app/work --output-dir /app/output
# Agent: 读 source_dump.md（S1/S2 均为【K】）→ 逐句润色写 chunks → 关键句回译+claims
python3 /skills/weekly-skill/scripts/claims_check.py --work-dir /app/work
python3 /skills/weekly-skill/scripts/terminology.py build --segments /app/work/source_segments.json --out /app/work
python3 /skills/weekly-skill/scripts/assemble.py --work-dir /app/work --output-dir /app/output --bilingual
python3 /skills/weekly-skill/scripts/validate_output.py --work-dir /app/work --output-dir /app/output
```

## 示意 chunk 行（示例）

```json
{"id":"abstract-B2-P1-S1","original":"The results of our experiments shows that the new catalyst can achieve a activity of 98.5%, which is much better than reported catalysts [2].","polished":"The experimental results show that the new catalyst achieves an activity of 98.5%, higher than reported catalysts [2].","decision":"modify","types":["grammar","register"],"reason":"主谓一致(show)、冠词(an)；much better 口语化改 higher；数值与引用守恒。回译一致","key":true,"claims":{"hedging":"中档（show）","numbers":"98.5%","units":"%","citations":"[2]","pointers":"无","causality":"无","negation":"无"}}
{"id":"abstract-B2-P1-S2","original":"This definitely proves the mechanism.","polished":"This is consistent with the proposed mechanism.","decision":"modify","types":["hedging"],"reason":"definitely proves 强断言与单实验证据不匹配，降至中档（consistent with）。回译一致；强度降级已列人工确认","key":true,"claims":{"hedging":"中档（consistent with）","numbers":"无","units":"无","citations":"无","pointers":"无","causality":"相关","negation":"无"}}
```

## 示意 drift_report.md（示例）

| 句 ID | 决策 | 回译结论 | 主张矩阵 |
|---|---|---|---|
| abstract-B2-P1-S1 | modify | 回译一致 | hedging=中档；numbers=98.5%；citations=[2] |
| abstract-B2-P1-S2 | modify | 回译一致（降档已列人工确认） | hedging=中档；causality=相关 |
