# CHANGELOG

## v1.0.0（2026-11-19，首版提交）
- 证据优先写作工作流：预检 → 材料索引（锚点）→ 事实底稿 → 分章写作 → 机读一致性核验 → 渲染 → 契约组装 → 终检。
- 七个纯标准库脚本 + run_pipeline.sh pre/post 两段韧性流水线，每段落盘 checkpoint，result.json 先行保底。
- check_consistency.py 五项机读核验：数字材料溯源、引用悬空/冗余、必备章节齐全、占位符闭环、文献字段提示。
- 支持六类任务：生成/改写/校对/结构化/双语/引用管理；渲染链 pandoc→python-docx、LibreOffice→xelatex 逐级降级如实记录。
- 交付：SKILL.md、README、6 份 references（含合成示例）、GITHUB_URL.txt。
