# 最小调用示例（示意输出，非正式案例结果）

输入（模拟）：稿件正文引用顺序为 [3]、[1,2]、[3,1]、[2]，文献表 4 条
（其中第 4 条从未被引用）。

```bash
SKILL_DIR=/skills/weekly-skill
python3 $SKILL_DIR/scripts/citation_sync.py audit manuscript.docx audit.json
```

示意输出（实际以真实运行为准）：

```json
{"issues": [
  {"kind": "uncited-reference", "num": 4},
  {"kind": "order-mismatch", "num": 3, "expected_first_position": 1},
  {"kind": "order-mismatch", "num": 1, "expected_first_position": 2},
  {"kind": "order-mismatch", "num": 2, "expected_first_position": 3}],
 "first_order": [3, 1, 2], "ref_count": 4, "citation_count": 4}
```

```bash
python3 $SKILL_DIR/scripts/citation_sync.py sync manuscript.docx synced.docx report.json
```

示意输出：

```json
{"ok": true, "spans_rewritten": 7, "issues": 1}
```

同步后：正文变为 [1]、[2,3]、[1,2]、[3]；文献表重排为
旧3→新1、旧1→新2、旧2→新3，旧4 保持表尾并在报告中列为未引用确认项。
