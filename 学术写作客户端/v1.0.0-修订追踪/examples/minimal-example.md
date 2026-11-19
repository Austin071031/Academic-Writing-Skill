# 最小调用示例（示意输出，非正式案例结果）

输入（模拟）：`/input/case.json` 指定 `case_id=W16-edit-001`，
`organizer-edit-workorder.json` 含 5 条修改指令，主稿件 `manuscript.docx`。

调用序列：

```bash
SKILL_DIR=/skills/weekly-skill
mkdir -p /app/work/originals /app/work/stage /app/output
cp -a /input/. /app/work/originals/

python3 $SKILL_DIR/scripts/docxkit.py dump /app/work/originals/manuscript.docx \
  > /app/work/stage/paras.json
python3 $SKILL_DIR/scripts/workorder.py /input /app/work/stage/paras.json \
  /app/work/stage/edit_plan.json
python3 $SKILL_DIR/scripts/revisions_apply.py \
  /app/work/originals/manuscript.docx /app/work/stage/edit_plan.json \
  /app/work/stage --edits-json /app/work/stage/edit_details.json
python3 $SKILL_DIR/scripts/render_preview.py /app/work/stage/revised_tracked.docx \
  /app/output/previews 3
python3 $SKILL_DIR/scripts/result_builder.py /input/case.json \
  /app/output/result.json --status success \
  --set 'revised_document=/app/output/previews/../revised_document.docx'
```

示意输出（实际数值以真实运行为准）：

```json
{"ok": true, "changes": "/app/work/stage/changes.json",
 "tracked": "/app/work/stage/revised_tracked.docx",
 "counts": {"applied": 4, "verified": 1, "failed": 0}}
```

```json
{"case_id": "W16-edit-001", "status": "success",
 "revised_document": "/app/output/revised_document.docx",
 "change_log": "/app/output/change_log.json",
 "previews": ["/app/output/previews/revised_document.pdf"],
 "uncertainty": [], "human_confirmations": [], "missing_fields": []}
```

修订稿在 Word/WPS 中打开后，“审阅→修订”面板可见逐条修订，
可逐条接受或拒绝；`accepted.docx` 为接受全部修订的净稿。
