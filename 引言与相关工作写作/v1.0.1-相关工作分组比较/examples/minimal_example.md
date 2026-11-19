# 最小调用示例（合成材料，非正式案例结果）

## 输入（合成）

文献库 5 条（references.bib），笔记 4 段，稿件含方法与结果。任务书要求按路线分组比较。

## 关键登记文件（示意）

grouping.json：

```json
{"groups": [
  {"gid": "G1", "theme": "均质包覆路线", "dimension_focus": "方法路线与长时局限",
   "entry_ids": ["R002", "R005"], "note": "工艺简单但长时开裂"},
  {"gid": "G2", "theme": "功能涂层路线", "dimension_focus": "方法路线、数据与评价",
   "entry_ids": ["R003", "R004"], "note": "性能与成本权衡"}
]}
```

comparison_rows.jsonl（一行示例）：

```json
{"entry_id": "R002", "problem_setting": "湿空气界面劣化", "method_route": "5 nm LiNbO3 均质包覆", "data_eval": "阻抗增长降 65%", "conclusion": "短时有效", "limitation": "24 小时以上保护层开裂"}
```

## 示意输出

group_related_work.py 打印：`组=2 引用=4 未入组=0 重复=0 时间序嫌疑=0 矩阵行=4 verdict=pass`。

comparison_matrix.md 渲染两组两张表；related_work.md 按 G1/G2 小节成稿并注入 [n]；
result.json 回填 output_contract 全部字段。
