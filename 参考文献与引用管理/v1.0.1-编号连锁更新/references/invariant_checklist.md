# 不变量终检清单（评审/Agent 双用）

引擎每次运行结束在 stdout 输出 `INVARIANTS: PASS|FAIL`，并同步写入
`work/renumber_report.json` 的 `invariants` 与 `PASS` 字段。以下清单与
`chain_update.md 第 5 节`一致，按此可独立复核：

## 数字编号模式

- [ ] **IV-1 数量守恒**：正文（含图注/表注/附录/脚注，**不含**文末列表段）引用的
  最大编号 == `references.json` 条数。`invariants.max_equals_list == true`。
- [ ] **IV-2 无缺口**：1..max 每个编号至少被引用一次。`invariants.no_gaps == true`。
  （注意：insert_existing 后若 Agent 忘了在正文补引，新条目号就是缺口——这正是
  IV-2 的设计用途。）
- [ ] **IV-3 无悬空**：`dangling_refs == []`。删除的每个旧号不再出现在任何非列表段。
- [ ] **IV-4 样式统一**：正文只出现一种引用样式。`invariants.style_consistent == true`。
- [ ] **IV-5 操作干净**：`ops_errors == []`（每个 edit op 都被正确执行）。
- [ ] **IV-6 映射完备**：`mapping` 覆盖旧列表 1..N；被删旧号的值为 `null`；
  新插入条目有 旧库号→新号 的恒等项。
- [ ] **IV-7 列表连续**：`references.json` 的 number 严格等于 1..len(entries)
  （validate_output.py 独立复检同一项）。

五项（IV-1..IV-5）全过 → PASS；任一不过 → FAIL，报告"不变量终检"节注明失败项。

## author-year 模式

- [ ] **AY-1** 报告含 `list_sorted_by_first_author` 结论；
- [ ] **AY-2** stale 条目全部列出（id + 原因 + 出处）；
- [ ] **AY-3** 报告显式说明"未做数字重排"。

## 复核命令

```bash
python3 -c "import json;r=json.load(open('/app/work/renumber_report.json'));print(r['PASS'],json.dumps(r['invariants'],ensure_ascii=False))"
python3 -c "import json;e=json.load(open('/app/output/references.json'))['entries'];assert [x['number'] for x in e]==list(range(1,len(e)+1));print('IV-7 OK')"
```
