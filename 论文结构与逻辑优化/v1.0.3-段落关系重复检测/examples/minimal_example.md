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
python3 $S/redundancy.py --work /app/work && \
python3 $S/report_builder.py --work /app/work --out /app/output \
  --focus redundancy --skill "paragraph-redundancy-map v1.0.3" && \
python3 $S/assemble_result.py --work /app/work --out /app/output \
  --skill "paragraph-redundancy-map v1.0.3" --status success && \
python3 $S/validate_output.py --out /app/output --work /app/work
```

## 示意输出（示例，非真实运行结果）

```
[inspect_case] case_id=demo-01 材料=3 稿件候选=1 语言=zh
[parse_manuscript] manuscript.md fmt=md 章节=6 段落=24 句子=112 字符=8640
[six_scan] findings=10 分布={'research_question': 1, 'section_structure': 1, ...}
[redundancy] pairs=2 near=1 sentdup=2 gaps=3 splits=1 findings=9
[report_builder] findings=15 -> diagnosis_report.md / edit_plan.json / findings.json
[assemble] status=success outputs=[...] 契约字段=[...]
[validate] PASS
```

`/app/output/diagnosis_report.md`（节选，示例）：

```
### [D5-01] 段落重复（跨章）（严重度 high / 置信度 0.87）
- 位置: 1 引言 ⇄ 2 相关工作 › P003⇄P005
- 原文锚点: “锂离子电池需求持续增长，硅基负极因高理论容量受到关注。然而硅在嵌锂过程中……”
- 判断依据: 两段字符 3-gram Jaccard=0.76（重复阈值 0.55）。跨章重复：保留 P003（1 引言，角色更核心），删除 P005（2 相关工作）的重复表述……
- 编辑动作 (merge): 跨章重复：保留 P003（1 引言），删除 P005（2 相关工作）的重复表述，改为一句交叉引用（'详见1 引言'）。
```
