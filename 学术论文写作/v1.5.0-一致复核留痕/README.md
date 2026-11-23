# consistency-audit-changelog（一致性复核与改稿留痕）

复核专精：任务分型+底稿快照 → 改动必留痕写作 → 三向审计（摘要↔正文/图表↔注/方法↔结果）+ 底稿逐段 diff。

## 快速开始
```bash
bash /skills/weekly-skill/scripts/run.sh pre    # 预检 + 任务分型 + 底稿快照
# Agent 写/改 sections/*.md，同步逐条写 change_log.md
cat /app/work/sections/*.md > /app/output/manuscript.md
bash /skills/weekly-skill/scripts/run.sh post   # 三向审计 + diff + 渲染 + result.json
```

## 文件
| 文件 | 作用 |
|-|-|
| `scripts/engine_pre.py` | 任务分型（generate/rewrite/proofread）+ 底稿逐段快照 + 术语基线 |
| `scripts/engine_check.py` | 三向一致性审计 + 底稿↔终稿 diff + change_log 空警告 |
| `references/audit_checklist.md` | 机读覆盖项、change_log 格式、勘误表格式、人工复核点 |

依赖：python3 ≥ 3.9（纯标准库）；系统工具可选降级。
作者：A0516（玻尔产品周赛第四期 写作01 参赛作品 v1.5.0）。
