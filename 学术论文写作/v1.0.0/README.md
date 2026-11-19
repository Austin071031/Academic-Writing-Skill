# academic-writing-evidence-first

证据优先的学术论文写作 Skill：围绕"写得实、引得对、全得起、改得动"四个目标，
把科研材料（PDF / CSV / TXT / MD / DOCX / 图片）转化为结构完整、事实可逐条回溯、可直接继续编辑的学术稿件。

## 解决什么问题
基础 Agent 直接写学术稿件的四大高频失败：
1. **数字臆造**：样本量、单位、统计量凭"合理感"补全；
2. **引用错配**：文献条目与论断不对应，作者/年份/DOI 失真，装饰性引用；
3. **章节缺项**：漏图注、漏数据可得性声明，缺失不标注；
4. **不可复核**：成稿后无法逐条指回材料位置，改动不留痕。

本 Skill 用"先溯源、后写作、先机读核验、后交付"的工作流解决：
确定性脚本完成材料索引（带锚点）、事实底稿（数值/单位/文献条目全溯源）、
一致性机读核验（数字溯源/引用悬空/章节缺项/占位符），Agent 只做分章写作与语义复核。

## 快速开始
```bash
# 运行环境：输入在 /input（case.json + task.md + 材料），技能安装在 /skills/weekly-skill
bash /skills/weekly-skill/scripts/run_pipeline.sh pre     # 预检+材料索引+事实底稿（全自动）
# Agent 读 /app/work/brief.json、materials_digest.md、facts_digest.md，按 SKILL.md 分章写作
bash /skills/weekly-skill/scripts/run_pipeline.sh post    # 核验+渲染+组装 result.json+终检
```
产物在 `/app/output/`：manuscript.md/docx、PDF/PNG 预览、evidence_map、consistency_report、result.json（含 output_contract 全部字段）。

## 依赖
- 必需：python3 ≥ 3.9（全部脚本仅用标准库）
- 可选降级：pdftotext/pdftoppm（PDF 提取与预览）、pandoc 或 python-docx（docx 生成）、LibreOffice（PDF 渲染）
- 缺失工具时对应产物标 unavailable 并给原因，不造假、不中断。

## 文件说明
| 文件 | 作用 |
|-|-|
| `SKILL.md` | 技能主说明：用途、输入输出、执行流程、异常处理（Agent 入口） |
| `scripts/inspect_case.py` | 预检 case.json/task.md → brief.json + result.json 保底骨架 |
| `scripts/build_material_index.py` | 材料 → 带锚点文本段索引 + 限长摘要 |
| `scripts/extract_facts.py` | 数值事实底稿 + 参考文献库（全溯源） |
| `scripts/check_consistency.py` | 数字溯源/引用对应/章节齐全/占位符 机读核验 |
| `scripts/render_preview.py` | md→docx→pdf→png 逐级降级渲染 |
| `scripts/assemble_result.py` | 按 output_contract 逐字段组装 result.json |
| `scripts/validate_output.py` | 交付终检（契约字段/产物存在性/状态自洽） |
| `scripts/run_pipeline.sh` | pre/post 两段韧性流水线，失败保底 partial |
| `references/fact_fidelity.md` | 事实保真红线（数字零臆造、趋势≠因果、缺失标注） |
| `references/citation_rules.md` | 论断—引用绑定与格式统一规则 |
| `references/section_templates.md` | IMRaD/单章/双语/改稿/校对/回复信 模板 |
| `references/consistency_checklist.md` | 机读+人工复核清单 |
| `references/output_schema.md` | result.json 字段与目录布局 |
| `references/worked_example.md` | 合成最小调用示例（已标明为示例） |

## 适用范围与限制
- 适用：有给定材料、有明确体裁/格式约束的学术写作、改写、校对、结构化、双语任务；中英文均可。
- 不适用：无材料自由选题写作（Skill 会说明并 partial 退出）。
- 限制：图片材料中的数值不自动读取（需 OCR/人工核对）；材料冲突时保留口径并标待确认，不擅自裁决；
  参考文献以外部检索补充时仅当任务明确允许且条目真实可查。

## 维护
作者：A0516（玻尔产品周赛第四期 写作01 参赛作品）。
问题与改进请通过 GitHub Issues 反馈。
