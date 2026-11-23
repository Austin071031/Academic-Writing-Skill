# material-evidence-indexing（材料组织与证据索引）

材料专精：带锚点材料索引 + 三登记（冗余/冲突/缺失）→ 挂锚点写作 + evidence_map → 三闭环核验（冲突/覆盖/数字）。

## 快速开始
```bash
bash /skills/weekly-skill/scripts/run.sh pre    # 预检 + material_index.md（含三登记）
# Agent 先裁决冲突，再按锚点写 sections/*.md，同步写 evidence_map.md
cat /app/work/sections/*.md > /app/output/manuscript.md
bash /skills/weekly-skill/scripts/run.sh post   # 三闭环 + 渲染 + result.json
```

## 文件
| 文件 | 作用 |
|-|-|
| `scripts/engine_pre.py` | 材料索引 + 冲突（同参数不同值）/冗余（近重复）/缺失三登记 |
| `scripts/engine_check.py` | 冲突闭环、材料覆盖闭环、数字溯源、evidence_map 存在性 |
| `references/material_rules.md` | 冲突裁决优先级、冗余处置、evidence_map 格式 |

依赖：python3 ≥ 3.9（纯标准库）；系统工具可选降级。
作者：A0516（玻尔产品周赛第四期 写作01 参赛作品 v1.4.0）。
