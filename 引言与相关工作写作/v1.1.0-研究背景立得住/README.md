# intro-background-grounding v1.1.0｜研究背景立得住

围绕"引言与相关工作写作"的参赛 Skill 版本之一，主攻**研究背景**方向：
背景段落逐句证据锚定（〔E#〕 锚点 + evidence_map 逐条回溯）+ 空转铺垫句式审计
（anti_fluff 引擎按统一清单检出"近年来受到广泛关注"类套话并给出改写建议）。

## 适用场景

- 给定论文底稿（方法/结果）+ 文献库 + 阅读笔记，要求起草或修改引言与相关工作；
- 背景段落存在空转铺垫、论断无出处、背景与研究问题脱节等问题的修复。

## 快速开始（Agent 视角）

1. `python3 scripts/init_result.py --case /input/case.json --out /app/output`
2. `python3 scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work`
3. 解析稿件/文献库/笔记（见 SKILL.md Phase 1 命令），`extract_facts.py` 出事实候选；
4. 按 SKILL.md Phase 3 写 evidence_map（含 cite 字段）、draft_intro、draft_rl、version_notes；
5. `anti_fluff.py` + `build_deliverables.py` 核验构建；`assemble_result.py` + `validate_output.py` + `render_previews.py` 收尾。

完整步骤见 [docs/USAGE.md](docs/USAGE.md)；最小示例见 [examples/minimal_example.md](examples/minimal_example.md)。

## 依赖

- Python 3.8+，纯标准库，无第三方依赖、无网络要求。
- 稿件为 .docx/.pdf 时分别用 zipfile/pdftotext 降级解析（pdftotext 缺失时如实记录）。

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、材料文件（格式不限，md/txt/tex/docx/pdf × bib/ris/enw/csv/json/GB-T 文本 × md/txt/json 笔记）。
- 输出（/app/output）：introduction.md、related_work.md、references.md、evidence_map.json、
  build_report.json、anti_fluff_audit.md、version_report.json、result.json、preview.html。

## 边界与限制

- 不臆造文献与数字；材料不足时交付 partial 并标注缺口。
- 引用编号由引擎统一生成（GB/T 7714 顺序编码）；需要著者-出版年制时需改造渲染函数。
- 适合中文学术写作；英文任务可运行（规则语言中立），但句式审计清单为中文口径。

## 仓库

https://github.com/Austin071031/Academic-Writing-Skill （目录：引言与相关工作写作/v1.1.0-研究背景立得住）
