# 最小调用示例（示意，非正式案例结果）

> 输入为合成文本；仅演示接口。

## 输入（合成）

一篇 12 节的长文档（论文+附录），解析后 80 个材料单元。

## 调用与示意输出

```bash
python3 $S/init_result.py && python3 $S/inspect_case.py && python3 $S/parse_materials.py --work /app/work
# Agent 设计 5 个一级分支（问题/方法/结果/结论/附录数据），写 mindmap.json 共 76 节点
python3 $S/map_audit.py --work /app/work
python3 $S/atlas.py --work /app/work --out /app/output
```

```
[atlas] 模式=atlas 总节点=76 图数=6 -> overview/topic_* + atlas_index.md + atlas.html
```

`atlas_index.md`（示意）：

```
# 图集索引（共 76 节点，6 张图）
- **overview**: 总览（根+一级分支），6 节点
- **topic_01**: 一级分支 q 的子树，4 节点（分支: 研究问题）
- **topic_02**: 一级分支 m 的子树，28 节点（分支: 方法）
- **topic_03**: 一级分支 r 的子树，31 节点（分支: 结果与证据）
...
```

`overview.svg` 中"方法"节点显示 `[分支规模 28 节点 → 详见对应 topic 图]`。
