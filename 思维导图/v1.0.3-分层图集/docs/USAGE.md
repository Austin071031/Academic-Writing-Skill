# 使用说明（mindmap-atlas v1.0.3）

## 调用（`$S=/skills/weekly-skill/scripts`）

```bash
# Phase 0
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_materials.py --work /app/work

# Phase 1-2：设计 4-7 个一级分支并写 work/mindmap.json（规范见 SKILL.md）

# Phase 3：审计
python3 $S/map_audit.py --work /app/work     # critical 修完重跑

# Phase 4：图集拆分与渲染
python3 $S/atlas.py --work /app/work --out /app/output
# 可选：--overview-budget 20 --topic-budget 40

# Phase 5：汇总与闸门
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "mindmap-atlas v1.0.3" --status success
python3 $S/validate_output.py --out /app/output --work /app/work
```

## 输出

| 模式 | 产物 |
|-|-|
| 单图（≤40 节点） | overview.{md,mm,opml,mmd,svg,html,png?} + atlas_index.md |
| 图集 | overview.*（根+一级分支+规模计数）+ topic_01..NN.* 各分支详图 + atlas_index.md + atlas.html |

中间件：`work/atlas/*.json`（每图的结构化源）、`work/atlas_index.json`（节点→图映射）。

## 阅读动线（交付说明里写给用户）

1. 先开 overview.html 看全局；2. 按分支规模进入对应 topic_XX.html 查细节；
3. 需要编辑时用同名 .mm（XMind/Freeplane）或 .opml；4. 任何节点凭 [Mxx-Sxx-Pxxx] 回
   evidence_map.json / materials.json 核对原文与页码。

## 自查

1. atlas_index.md 中各图节点数 ≤ 预算；2. 索引 node_ids 并集 = 全图节点（截断分支除外，
   截断必须在 uncertainty 声明）；3. 每图文件非空；4. validate PASS。

## 失败处理

某张详图渲染失败不阻塞其他图：追加 `work/exceptions.json`，其余图照交，
`--status partial` 并在 uncertainty 指明哪张图缺失。
