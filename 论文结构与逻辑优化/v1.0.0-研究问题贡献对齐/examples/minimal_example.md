# 最小调用示例（示意输出，非正式案例结果）

## 输入

`/input/` 下放 `case.json`（含 case_id 与 output_contract）、`task.md`、`manuscript.md`（任意完整稿件）。

## 调用

```bash
S=/skills/weekly-skill/scripts
python3 $S/init_result.py && \
python3 $S/inspect_case.py --work /app/work && \
python3 $S/parse_manuscript.py --work /app/work && \
python3 $S/six_scan.py --work /app/work && \
python3 $S/rq_engine.py --work /app/work && \
python3 $S/report_builder.py --work /app/work --out /app/output \
  --focus research_question --skill "rq-contribution-alignment v1.0.0" && \
python3 $S/assemble_result.py --work /app/work --out /app/output \
  --skill "rq-contribution-alignment v1.0.0" --status success && \
python3 $S/validate_output.py --out /app/output --work /app/work
```

## 示意输出（示例，非真实运行结果）

```
[inspect_case] case_id=demo-01 材料=3 稿件候选=1 语言=zh
[parse_manuscript] manuscript.md fmt=md 章节=8 段落=42 句子=187 字符=15230
[six_scan] findings=11 分布={'research_question': 2, 'section_structure': 2, ...}
[rq_engine] RQ=2 贡献=3 无呼应=1 深度findings=5
[report_builder] findings=16 -> diagnosis_report.md / edit_plan.json / findings.json
[assemble] status=success outputs=[...] 契约字段=[...]
[validate] PASS
```

`/app/output/diagnosis_report.md`（节选，示例）：

```
### [D1-02] 研究问题无方法/实验承接（严重度 high / 置信度 0.7）
- 位置: 1 引言 › P003 › P003-s2
- 原文锚点: “本文旨在揭示界面稳定性对循环寿命的影响。”
- 判断依据: 该 RQ 内容词在方法章覆盖率 0.08、实验章 0.11（阈值 0.20）……
- 编辑动作 (add): 在方法章显式说明界面稳定性的表征方案如何回答此 RQ……
```
