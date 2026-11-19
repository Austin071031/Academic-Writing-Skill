# 合成测试文本（全部标注"合成"，非真实文献/案例）

用于本地回归与评审复现。每场景给出：输入要点、edit_ops、期望结论。

## 场景 T1：删除中间条目 + 区间引用 + 图表注引用（合成）

稿件（节选，6 条列表）：

```markdown
引言综述了该领域二十年进展[1-5]。

图 2 给出关键对比[2,5]。

表 1 汇总参数[3,6]。

## 参考文献
[1]…[6]（略，任意 6 条合成条目）
```

edit_ops：`[{"op":"delete","ref_id":"4","note":"合成：删除第 4 条"}]`

期望：先 FAIL——悬空 1 处（引言 `[1-5]` 含旧号 4）；Agent 把引言改为 `[1-3,5]` 后
重跑 PASS；正文 `[1-3,5]` → `[1-3,4]`（原 5 变 4），图注 `[2,5]`→`[2,4]`，
表注 `[3,6]`→`[3,5]`；列表 5 条连续。

## 场景 T2：删除中间条目（不修复）→ 悬空必须报（合成）

同 T1 输入，edit_ops 同，Agent 不修复任何句子。
期望：FAIL；悬空清单含引言段（raw `[1-5]`，旧号 `[4]`）；mapping 中 4=null；
报告"结论: FAIL"。**这是诚实性测试：引擎不得静默通过。**

## 场景 T3：两章合并 + merge 去重（合成）

任务书（合成）："将第 2 章并入第 3 章；文献 2 与文献 7 为同一工作，保留 7；
删除文献 5。"
edit_ops：

```json
[{"op":"merge","ref_ids":["R002","R007"],"keep":"R007","note":"合成"},
 {"op":"delete","ref_id":"R005","note":"合成"}]
```

期望：mapping 2=null、5=null、7→5；若正文有 `[2,5,7]` 类句子则先报悬空；
Agent 改写后 PASS，列表 5 条。

## 场景 T4：insert_existing 从库中拉入 + 正文直引库编号（合成）

文献库 7 条，稿件列表仅 6 条（Agent 已写 work/reference_list.json 6 条）。
edit_ops：`[{"op":"insert_existing","ref_id":"R007","to":1,"note":"合成"}]`
Agent 在正文补一句引用 `[7]`。
期望：PASS；`[7]`→`[1]`；mapping 含 `"7": 1`；references.json 第 1 条 id=R007 且
含 source_file/source_index。
反例：Agent 忘记补正文引用 → IV-2 缺口 FAIL（`gaps` 含 1），提示补引。

## 场景 T5：著者-出版年分流（合成）

稿件正文 `(张三, 2019)`、`(李四, 2021)`，文末列表未按作者排序、其中一条缺年份。
期望：引擎走 author-year 模式；报告 `list_sorted_by_first_author: false`、stale 1 条；
正文零改动；PASS 依据见 references/author_year_mode.md。

## 复现方式

```bash
# 任一场景：按 docs/USAGE.md 第 1 节流水线执行；
# 引擎终检以 stdout 末行为准：
python3 scripts/renumber_plan.py --work work --out output --engine scripts/cite_engine.py
# 期望最后一行：INVARIANTS: PASS（T2/T4 反例期望 FAIL）
```
