# 使用说明（concept-relation-mapper v1.0.2）

## 调用（`$S=/skills/weekly-skill/scripts`）

```bash
# Phase 0
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_materials.py --work /app/work

# Phase 1：Agent 写 work/mindmap.json（层级 + edges，规范见 SKILL.md）

# Phase 2：双层审计
python3 $S/map_audit.py --work /app/work
python3 $S/relation_engine.py audit --work /app/work
# 读 work/audit.json 与 work/relation_audit.json，修订后重跑

# Phase 3：渲染与交付
python3 $S/map_render.py --work /app/work --out /app/output
python3 $S/relation_engine.py render --work /app/work --out /app/output
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "concept-relation-mapper v1.0.2" --status success
python3 $S/validate_output.py --out /app/output --work /app/work
```

## relation_audit.json 判读

| 字段 | 含义 | 动作 |
|-|-|-|
| issues[].edge_endpoint | 边端点不存在 | critical，修正 id |
| issues[].edge_direction_conflict | 双向有向边冲突 | critical，核实后留一条 |
| issues[].edge_no_evidence | 边无证据也未注明推断 | warning，补证据或删边 |
| candidates[].conflict_candidate | 同主体不同数字 | 核实：修正或加 conflicts 边 |
| candidates[].missing_relation_candidate | 共享证据但无边 | 评估补 supports/cites |

## 输出

- 层级导图：mindmap.md/.mm/.opml/.mmd/.svg/.html（+.png 视环境）
- 关系图：relations.mmd（Mermaid flowchart）、relations.svg（分层 DAG）、relations.md（关系表）
- 证据与审计：evidence_map.json、audit_report.json、result.json

## 自查

1. 两份审计 critical=0；2. 每条边能回答"依据哪个单元"；3. 结论节点有 supports 入边；
4. validate_output PASS。

## 失败处理

失败追加 `work/exceptions.json`；无法修复的冲突保留双方并标 uncertain；
`--status partial` + `work/uncertainty.json` 说明。
