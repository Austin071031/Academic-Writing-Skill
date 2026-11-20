# 最小调用示例（合成示例，仅示意接口与流程，非正式案例结果）

底稿句子：“该药物显著降低血压，且安全性良好。” 切分与匹配示意：

claims.jsonl
```json
{"claim_id":"C01","claim_text":"该药物可降低血压","status":"supported","evidence_ids":["E01","E02"]}
{"claim_id":"C02","claim_text":"该药物安全性良好","status":"conflicting","evidence_ids":["E03","E04"]}
{"claim_id":"C03","claim_text":"该药物优于现有标准治疗","status":"unsupported","evidence_ids":[]}
```

claim_source_matrix.csv
```csv
claim_id,evidence_id,support_type,support_scope
C01,E01,direct,"结果：收缩压下降 8 mmHg (p.212)"
C01,E02,direct,"结果：舒张压下降 5 mmHg (p.212)"
C02,E03,direct,"结果：不良反应率与安慰剂相当 (p.215)"
C02,E04,conflicting,"结果：肝功能异常升高 3 例 (p.216)"
```
C03 无支撑 → 写入 open_questions，成稿不得出现“优于标准治疗”的表述。
