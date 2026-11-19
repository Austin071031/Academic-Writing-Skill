# 最小调用示例（示意输出，非正式案例结果）

```bash
SKILL_DIR=/skills/weekly-skill
mkdir -p /app/work/vault

# 原稿快照（author 来源）
python3 $SKILL_DIR/scripts/lineage.py snapshot manuscript.docx /app/work/vault \
  --label original --source author
# 示意：{"rev": "f35de3cb9be4", "parent": null, "paragraphs": 24, ...}

# 修改后快照（parent 指向原稿）
python3 $SKILL_DIR/scripts/lineage.py snapshot revised.docx /app/work/vault \
  --label terminology-unify --parent f35de3cb9be4 --source skill
# 示意：{"rev": "540013347422", "parent": "f35de3cb9be4", ...}

# 版本对比与回退
python3 $SKILL_DIR/scripts/lineage.py diff /app/work/vault f35de3cb9be4 540013347422
# 示意：{"changed_paragraphs": 19, "changes": [{"para_index": 0, ...}]}
python3 $SKILL_DIR/scripts/lineage.py restore /app/work/vault f35de3cb9be4 restored.docx
# 示意：{"ok": true, "restored": "restored.docx", "sha256_verified": true}
python3 $SKILL_DIR/scripts/lineage.py verify /app/work/vault
# 示意：{"ok": true, "total": 2, "corrupted": []}
```
