# citation-integrity-binding（引用核验与论断绑定）

参考文献与引用管理专精：文献库（唯一引用来源）→ 带引用写作（论断绑定红线）→ 五检（悬空/装饰性/编号/格式/字段）+ 绑定复核表。

## 快速开始
```bash
bash /skills/weekly-skill/scripts/run.sh pre    # 预检 + 文献库 library.md
# Agent 读 brief.json、library.md，按 SKILL.md 红线写 sections/*.md
cat /app/work/sections/*.md > /app/output/manuscript.md
bash /skills/weekly-skill/scripts/run.sh post   # 引用五检 + 渲染 + result.json
```

## 文件
| 文件 | 作用 |
|-|-|
| `scripts/engine_pre.py` | 材料 → 文献库 library.json（作者/年份/DOI/锚点/缺字段标记） |
| `scripts/engine_check.py` | 引用五检 + 论断—引用绑定表生成 |
| `scripts/inspect_case.py` / `finalize.py` / `run.sh` | 预检 / 收尾 / 管线 |
| `references/binding_rules.md` | 绑定类型、装饰性引用识别、错配处置 |
| `references/citation_styles.md` | GB/T 7714 / APA / IEEE / Vancouver 模板 |

依赖：python3 ≥ 3.9（纯标准库）；pdftotext/pandoc/LibreOffice/pdftoppm 可选降级。
限制：材料无文献条目时不虚构，写 uncertainty 降级为格式检查。
作者：A0516（玻尔产品周赛第四期 写作01 参赛作品 v1.2.0）。
