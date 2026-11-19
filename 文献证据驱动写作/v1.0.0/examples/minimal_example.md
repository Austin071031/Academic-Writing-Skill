# 最小调用示例（合成示例，仅示意接口与流程，非正式案例结果）

输入（节选 case.json）：
```json
{"case_id": "DEMO-01",
 "task": "从给定 2 篇 PDF 中提取支持'运动干预改善糖化血红蛋白'的可用证据",
 "materials": ["pdf/exercise_hbA1c_trial.pdf", "pdf/review_diabetes.pdf"],
 "output_contract": {"deliverable": null, "evidence_table": null}}
```

执行：
```bash
bash /skills/weekly-skill/scripts/run_pipeline.sh /input /app/work /app/output
# 读取 /app/work/brief.json 与 text_manifest.json 后按 SKILL.md 阶段1-5 执行
```

示意产物（节选）：
evidence.csv
```csv
evidence_id,doc_id,location,quote,doc_type,support_type,strength,claim_ids
E01,D01_exercise_hbA1c_trial,p.214,"HbA1c decreased by 0.6% (95% CI 0.3–0.9) in the exercise group relative to control.",primary_study,direct,B,C01
E02,D02_review_diabetes,p.8,"多数纳入研究报告了运动组糖化血红蛋白的显著下降，但研究间异质性较高。",review,partial,C,C01
```
claims.jsonl
```json
{"claim_id":"C01","claim_text":"运动干预可降低 2 型糖尿病患者糖化血红蛋白约 0.6%","status":"partial","evidence_ids":["E01","E02"],"notes":"单项 RCT 直接支持；综述方向一致但强调异质性"}
```
result.json（节选）
```json
{"case_id":"DEMO-01","deliverable":"draft.md","evidence_table":"evidence.csv","status":"success","assumptions":["目标读者按期刊读者处理"],"uncertainty":["综述未给出合并效应量"],"exceptions":[]}
```
