# CHANGELOG

## v1.0.4（2026-11-19）
- 首版：文体转换方向（接得住）。
  - `genre_engine.py map`：4 套内置文体模板（科普文章/新闻通稿/项目申报材料/简报），
    按 inspection.genre 选模板（未识别默认科普文章并记 manual_confirmations），
    源文段落按内容关键词映射到模板要素，缺失要素标注「源文未提供」。
  - `genre_engine.py ledger`：结合 alignment.json 与 Agent 逐段理由（change_reasons.jsonl）
    生成逐段对照台账——源文段落覆盖核查（无理由删除=critical）、改写段落溯源
    （新增未标「新增-过渡」=warn、新增含数值提示核对源外事实、理由动作与对齐矛盾=warn），
    输出 change_ledger.json + 人读 traceability_report.md。
- 共享核心：case 解析、源文结构化（事实清单/缩写/术语候选）、源文-改写逐段对齐。
- 诚实交付：骨架 result.json 防超时空手，validate 发布闸门，partial 如实降级。
