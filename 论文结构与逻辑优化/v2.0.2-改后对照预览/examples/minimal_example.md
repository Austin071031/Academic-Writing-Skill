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
python3 $S/section_flow.py --work /app/work && \
python3 $S/report_builder.py --work /app/work --out /app/output \
  --focus section_structure --skill "section-narrative-flow v1.0.1" && \
python3 $S/assemble_result.py --work /app/work --out /app/output \
  --skill "section-narrative-flow v1.0.1" --status success && \
python3 $S/validate_output.py --out /app/output --work /app/work
```

## 示意输出（示例，非真实运行结果）

```
[inspect_case] case_id=demo-02 材料=3 稿件候选=1 语言=zh
[parse_manuscript] manuscript.md fmt=md 章节=7 段落=38 句子=171 字符=14120
[six_scan] findings=12 分布={'section_structure': 3, 'argument_chain': 2, ...}
[section_flow] 章节=7 逆序对=1 未定义缩写=3 深度findings=8
[report_builder] findings=18 -> diagnosis_report.md / edit_plan.json / findings.json
[assemble] status=success outputs=[...] 契约字段=[...]
[validate] PASS
```

`/app/output/diagnosis_report.md`（节选，示例）：

```
### [D2-01] 章节顺序与论证顺序倒置（严重度 high / 置信度 0.7）
- 位置: 3 方法
- 原文锚点: “3 方法”
- 判断依据: 章节角色序列表出现逆序对：method 先于 results（规范序 摘要→…→方法→实验→结果→…）……
- 编辑动作 (move): 将「3 方法」移至「2 结果」之前，恢复 引言→方法→结果 的论证顺序……
```

`/app/work/restructured_outline.md`（节选，示例）：

```
## 二、建议叙事顺序（按论证链）
1. 1 引言（SEC2，角色=introduction）
2. 3 方法（SEC4，角色=method）  ← 建议：移动
3. 2 结果（SEC3，角色=results）
```
