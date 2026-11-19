# related-work-grouping v1.0.1｜相关工作分得清

参赛 Skill 版本之二，主攻**相关工作组织**方向：按方法路线/问题设定分组，引擎校验
"引用条目 ↔ 分组"双向一致、检测逐篇罗列与时间序、渲染五维比较矩阵（问题设定/方法路线/数据与评价/结论/局限）。

## 适用场景

- 给定文献库（+笔记+底稿），要求整理/起草相关工作；
- 修复逐篇摘要拼接、按年份罗列、分组遗漏、转述失真的相关工作草稿。

## 快速开始

按 SKILL.md 阶段执行：Phase 0–1 解析（init_result → inspect → parse_* → extract_facts）；
Phase 3 写 evidence_map / grouping.json / comparison_rows.jsonl / draft_rl.md / draft_intro.md /
claim_bindings.jsonl；Phase 4 跑 `group_related_work.py` + `build_deliverables.py`；
收尾 assemble → validate → render_previews。详见 [docs/USAGE.md](docs/USAGE.md)。

## 依赖与边界

- Python 3.8+ 纯标准库；无网络依赖。
- 引用编号由引擎统一注入；比较矩阵内容需 Agent 据材料填写，引擎渲染并审计覆盖完整性。

## 仓库

https://github.com/Austin071031/Academic-Writing-Skill （目录：引言与相关工作写作/v1.0.1-相关工作分组比较）
