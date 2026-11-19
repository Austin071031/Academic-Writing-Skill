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
python3 $S/boundary_audit.py --work /app/work && \
python3 $S/report_builder.py --work /app/work --out /app/output \
  --focus conclusion_boundary --skill "conclusion-boundary-check v1.0.4" && \
python3 $S/assemble_result.py --work /app/work --out /app/output \
  --skill "conclusion-boundary-check v1.0.4" --status success && \
python3 $S/validate_output.py --out /app/output --work /app/work
```

## 示意输出（示例，非真实运行结果）

```
[inspect_case] case_id=demo-01 材料=3 稿件候选=1 语言=zh
[parse_manuscript] manuscript.md fmt=md 章节=6 段落=18 句子=64 字符=8200
[six_scan] findings=9 分布={'research_question': 1, 'conclusion_boundary': 3, ...}
[boundary_audit] nums=7 ok=3 approx=1 stray=2 causal=2 over=1 findings=6
[report_builder] findings=13 -> diagnosis_report.md / edit_plan.json / findings.json
[assemble] status=success outputs=[...] 契约字段=[...]
[validate] PASS
```

`/app/output/diagnosis_report.md`（节选，示例）：

```
### [D6-01] 结论/摘要数字无正文出处（无源数字）（严重度 high / 置信度 0.75）
- 位置: 4 结论 › P005 › P005-s1
- 原文锚点: “首效达到 91.0%。”
- 判断依据: 数字 91.0% 在方法/实验/结果/讨论章无逐字命中、无数值相等、最近源数字为 87.3%（3 结果），相对差 4.07% 在容差内但无法由舍入得到……
- 编辑动作 (narrow): 为该数字补正文出处（指向具体表格/小节），或从结论中删除或改为正文已有数值。
```
