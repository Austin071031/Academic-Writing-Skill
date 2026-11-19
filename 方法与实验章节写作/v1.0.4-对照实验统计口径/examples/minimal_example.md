# 最小调用示例（合成材料，标注为示例，非正式案例结果）

## 输入（合成）

同前：`case.json`（demo-05）+ 合成材料。train.log 给出本文 acc=0.913；基线数值未提供。

## 关键差异：实验矩阵

`work/experiment_matrix.json`（节选，示意）：

```json
[{"rid": "R1", "variant": "Ours", "is_baseline": false, "dataset": "SynthBench v1.2",
  "split": "test", "metric": "Accuracy", "budget": "10 epochs", "seed": 42, "repeats": 1,
  "value": "0.913", "single_run_note": "单次运行", "source_eid": "E0020"},
 {"rid": "R2", "variant": "BERT-base", "is_baseline": true, "dataset": "SynthBench v1.2",
  "split": "test", "metric": "Accuracy", "budget": "10 epochs", "seed": 42, "repeats": 1,
  "value": "未在材料中给出", "single_run_note": "—", "source_eid": ""}]
```

```bash
python3 /skills/weekly-skill/scripts/exp_matrix.py --work /app/work --out /app/output
# -> comparability_report.json: rows=2 baselines=1 issues=[] verdict=pass
# （若第五节未引用 R1/R2 或把 R2 的 budget 改成 20 epochs，issues 非空 fail——示意行为）
```

正文第五节（示意）："本文方法（R1）单次运行 Accuracy 为 91.3%〔E0020〕；BERT-base 基线
（R2）结果未在材料中给出，已列入附录C追问作者——本节暂不作优劣结论。"
