# Minimal Example（示例，非正式案例结果）

合成最小案例：3 条文献的顺序编码制稿件，任务书要求"删除文献 2，并把文献 3 调到首位"。

## 输入

manuscript.md：

```markdown
# 示例稿

方法 A 已广泛用于该领域[1-2]。方法 B 是近年改进[3]。

图 1 方法对比[2,3]。

## 参考文献

[1] 王一. 方法 A 研究[J]. 学报, 2020, 1(1): 1-5.

[2] 王二. 方法 A 补充[J]. 学报, 2021, 2(2): 6-9.

[3] 李三. 方法 B 改进[J]. 新技术, 2022, 3(3): 10-15.
```

library.bib 含对应 3 条 @article 记录（解析后 id 为 R001…R003）。

## 调用

```bash
python3 scripts/parse_manuscript.py manuscript.md --work work
python3 scripts/parse_library.py library.bib --work work
cat > work/edit_ops.json <<'EOF'
[{"op": "delete", "ref_id": "2", "note": "任务书：删除文献 2"},
 {"op": "reorder", "ref_id": "R003", "to": 1, "note": "任务书：文献 3 调到首位"}]
EOF
python3 scripts/renumber_plan.py --work work --out output --engine scripts/cite_engine.py
```

注意：任务书删文献 2，而正文 `[1-2]` 与图 1 注 `[2,3]` 都引用了它 → 引擎会报悬空（见下）。

## 示意输出（标注：示例，非正式案例结果）

```
[renumber_plan] 映射 2 条, 删除 1 条, 悬空段落 2 处
INVARIANTS: FAIL
```

output/renumber_report.md 摘录：

```markdown
## 3. 悬空引用清单（删除后仍被引用，须 Agent 处置）
- 段落 P002（body）标记 [1-2] 涉及已删除旧号 [2]
  - 处置: Agent 必须改写该句（删该引或改引存活条目）后重跑引擎
- 段落 P003（figure_note）标记 [2,3] 涉及已删除旧号 [2]
  - 处置: Agent 必须改写该句（删该引或改引存活条目）后重跑引擎
```

Agent 把 `work/manuscript.json` 中 P002 改为"……该领域[1]。"、P003 改为
"图 1 方法对比[3]。"后重跑：

```
[renumber_plan] 映射 2 条, 删除 1 条, 悬空段落 0 处
INVARIANTS: PASS
```

output/references.md：

```markdown
## 参考文献

[1] 李三. 方法 B 改进[J]. 新技术, 2022, 3(3): 10-15.

[2] 王一. 方法 A 研究[J]. 学报, 2020, 1(1): 1-5.
```

output/edited_manuscript.md 正文段：`方法 A 已广泛用于该领域[2]。方法 B 是近年改进[1]。`
`图 1 方法对比[1]。`——正文、图注、列表三者编号一致，1..2 无缺口。
