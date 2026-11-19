# 最小调用示例（示意输出，非正式案例结果）

```bash
SKILL_DIR=/skills/weekly-skill

# 1. 字体检查
python3 $SKILL_DIR/scripts/fidelity_export.py font-check revised.docx fonts.json
# 示意：{"fonts_in_document": ["Times New Roman"], "substitutions": []}

# 2. 渲染
python3 $SKILL_DIR/scripts/fidelity_export.py render revised.docx out 3
# 示意：{"pdf": "out/revised.pdf", "pngs": ["out/revised-1.png", "out/revised-2.png"],
#       "renderer": "libreoffice", "ok": true}

# 3. 目录页码回填（两遍渲染）
python3 $SKILL_DIR/scripts/fidelity_export.py toc-refresh revised.docx out/revised.pdf \
  revised_toc.docx toc.json
# 示意：{"has_toc_field": true, "headings_found": 6, "refreshed": 6}

# 4. 保真差分
printf '%s\n' '杨氏模量' > whitelist.txt
python3 $SKILL_DIR/scripts/fidelity_export.py fidelity original.docx revised_toc.docx \
  whitelist.txt fidelity.json
# 示意：{"summary": {"structural_breaks": 0, "expected_change_hits": 2},
#       "fidelity_breaks": []}
```
