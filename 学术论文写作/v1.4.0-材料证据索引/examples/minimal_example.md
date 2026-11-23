# 最小调用示例（合成示例，非正式测试案例）

输入：task.md（"依据全部材料写结果节"）、data.csv（n=3）、notes.md（记录 n=5）、draft.md（底稿）。

```bash
bash /skills/weekly-skill/scripts/run.sh pre
# → material_index.md：冲突登记——参数 "每组重复 n": 3(M01#l2) vs 5(M02#l4)
# Agent 裁决：notes.md 为实验记录但与 CSV 行数矛盾，CSV 为原始数据 → 采 n=3，change_log 留痕
# 写稿 + evidence_map.md（论断 12 条全挂锚点；draft.md 注"底稿仅作结构参考"）
bash /skills/weekly-skill/scripts/run.sh post
# → material_audit.md：冲突已闭环、材料全覆盖、数字 15/15 有出处 → PASS
```
