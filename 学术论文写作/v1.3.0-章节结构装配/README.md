# structure-completeness-assembly（章节结构与完整性装配）

章节专精：章节×材料装配骨架 → 按骨架写稿（缺项显式【待补】）→ 完整性五检（章节/声明/层级/图表注/篇幅）。

## 快速开始
```bash
bash /skills/weekly-skill/scripts/run.sh pre    # 预检 + outline.md 装配骨架
# Agent 按骨架写 sections/*.md，无材料节标【待补：缺材料】
cat /app/work/sections/*.md > /app/output/manuscript.md
bash /skills/weekly-skill/scripts/run.sh post   # 完整性五检 + 渲染 + result.json
```

## 文件
| 文件 | 作用 |
|-|-|
| `scripts/engine_pre.py` | 材料×章节关键词命中 → outline.md（支撑/缺口/篇幅配额） |
| `scripts/engine_check.py` | 必备章节、声明字段、层级连续、图表注、篇幅比例五检 |
| `references/section_templates.md` | IMRaD/摘要/回复信/Cover letter 模板与内容清单 |
| `references/declarations.md` | 数据可得性/利益冲突/作者贡献/基金 声明字段库 |

依赖：python3 ≥ 3.9（纯标准库）；系统工具可选降级。
作者：A0516（玻尔产品周赛第四期 写作01 参赛作品 v1.3.0）。
