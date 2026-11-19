# 最小调用示例（示意输出，非正式案例结果）

分解示例（edit_details.json）：

```json
{
  "E1": {"type": "replace", "old": "弹性模量", "new": "杨氏模量",
         "level": "术语", "basis": "指令要求术语统一，事实不变"},
  "E2": {"type": "delete", "old": "然而，现有方法存在精度不足的问题[2]。",
         "level": "结构", "basis": "指令明确要求删除该句"},
  "E3": {"type": "note", "level": "核对",
         "basis": "结论数字与结果节一致，无需改写"}
}
```

守卫调用与示意输出：

```bash
python3 $SKILL_DIR/scripts/drift_guard.py original.docx accepted.docx \
  changes.json drift_report.json
```

```json
{"anchors": {"ok": 5, "failed": []},
 "rewrite_warnings": [],
 "unauthorized_changes": [],
 "number_drift": [],
 "max_rewrite_ratio": 0.5,
 "verdict": "clean"}
```

负例（整段重写会被抓住）：

```json
{"rewrite_warnings": [{"rewrite_ratio": 0.71, "note": "改写幅度超过阈值，需确认指令授权"}],
 "verdict": "warning"}
```
