# results-transcription-data-fidelity（结果与图表转写）

数据保真专精的学术写作 Skill：数值台账（唯一数字来源）→ 结果节与图注写作 → 数字回写机读核验。

## 快速开始
```bash
bash /skills/weekly-skill/scripts/run.sh pre    # 预检 + 数值台账
# Agent 读 /app/work/brief.json、facts_ledger.md，按 SKILL.md 红线写 /app/work/sections/*.md
cat /app/work/sections/*.md > /app/output/manuscript.md
bash /skills/weekly-skill/scripts/run.sh post   # 数字核验 + 渲染 + result.json + 终检
```

## 文件
| 文件 | 作用 |
|-|-|
| `scripts/inspect_case.py` | 预检 case.json/task.md → brief.json + result.json 保底骨架 |
| `scripts/engine_pre.py` | 数据材料 → facts_ledger（数值台账，带锚点） |
| `scripts/engine_check.py` | 数字溯源核验 + 图注规范检查 + 因果措辞警告 |
| `scripts/finalize.py` | 渲染预览 + 按 output_contract 组装 result.json + 终检 |
| `scripts/run.sh` | pre/post 两段管线 |
| `references/results_writing.md` | 结果段组织、图注公式、统计口径、趋势≠因果三档措辞 |

## 依赖
python3 ≥ 3.9（纯标准库）；pdftotext/pdftoppm/pandoc/LibreOffice 可选，缺失自动降级并如实记录。

## 限制
图片材料中的数值不自动读取（标待确认）；材料冲突时保留口径并标注，不擅自裁决。
作者：A0516（玻尔产品周赛第四期 写作01 参赛作品 v1.1.0）。
