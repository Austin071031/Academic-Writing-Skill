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
python3 $S/chain_audit.py --work /app/work && \
python3 $S/report_builder.py --work /app/work --out /app/output \
  --focus argument_chain --skill "argument-chain-audit v1.0.2" && \
python3 $S/assemble_result.py --work /app/work --out /app/output \
  --skill "argument-chain-audit v1.0.2" --status success && \
python3 $S/validate_output.py --out /app/output --work /app/work
```

## 示意输出（示例，非真实运行结果）

```
[inspect_case] case_id=demo-01 材料=3 稿件候选=1 语言=zh
[parse_manuscript] manuscript.md fmt=md 章节=6 段落=18 句子=52 字符=3100
[six_scan] findings=9 分布={'argument_chain': 2, 'conclusion_boundary': 2, ...}
[chain_audit] claims=11 strong=4 weak=2 none=5 findings=7
[report_builder] findings=16 -> diagnosis_report.md / edit_plan.json / findings.json
[assemble] status=success outputs=[...] 契约字段=[...]
[validate] PASS
```

`/app/output/diagnosis_report.md`（节选，示例）：

```
### [D3-02] 论证链断裂：论断窗口内无论据锚点（严重度 high / 置信度 0.7）
- 位置: 4 讨论 › P006 › P006-s1
- 原文锚点: “超孔结构的引入显著改善了倍率性能。”
- 判断依据: 该论断句（因果论断）所在句、所在段及相邻段均无引用、图表或带单位数字锚点，论断悬空。
- 编辑动作 (narrow): 删除或降级该论断，或补可核验证据（数据、图表或引用）并显式指回（"见表X/图Y/[n]"）。
```

`work/chain_audit.json`（节选，示例）：

```json
{"summary": {"n_claims": 11, "strong": 4, "weak": 2, "none": 5, "n_findings": 7},
 "claims": [{"sentence_id": "P006-s1", "types": ["因果论断"], "support": "none", ...}]}
```
