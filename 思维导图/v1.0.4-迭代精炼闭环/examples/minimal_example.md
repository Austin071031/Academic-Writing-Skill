# 最小调用示例（示意，非正式案例结果）

> 输入为合成文本；仅演示接口。

## 输入（合成）

一篇含 3 个定量结果的短文 + 一份含下一步计划的笔记。

## 调用与示意输出

```bash
python3 $S/parse_materials.py --work /app/work
# Agent 快速草稿：12 节点，只覆盖了结果 1，结论无 supports 边
python3 $S/map_audit.py --work /app/work
python3 $S/refine.py --work /app/work
```

```
[refine] 综合分=61.3 修复项=5 -> refine_report.json / fix_list.md
```

`fix_list.md`（示意）：

```
# 修复清单（综合分 61.3/100）
五维得分: 抓得准 100 ｜ 理得清 94 ｜ 连得对 42 ｜ 可追溯 38 ｜ 实际有用 70
1. **[high]** 重要单元 M01-S04-P001 未被任何节点覆盖（结果 2: 循环寿命从 800 提升至 1400 次…）
2. **[high]** 仅 5/12 节点挂证据，事实性节点必须挂 evidence
3. **[medium]** 全图仅 1 条关系边；为因果/支持关系补边并挂证据
...
```

Agent 补结果 2/3 节点、给结论补 supports 边后复评：

```
[refine] 综合分=88.6 修复项=1
```

stats.json 记录 `{"refine_rounds":[{"overall":61.3},{"overall":88.6}]}` 作为增益证据。
