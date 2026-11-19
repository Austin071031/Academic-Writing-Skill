# CHANGELOG

## v1.0.3（2026-11-19）
- 首版：术语锁定与跨文体一致方向。
- terminology_engine.py candidates：机选术语表草稿——全称↔缩写配对（含"缩写（全称）"反向）、
  相似度≥0.70 中文异写聚类（共享字符覆盖/最长公共子串/编辑相似度取最大）、
  大小写/连字符/空格变体归一化归并、化学式识别（LiNbO3/NCM811/LiNi0.8Co0.1Mn0.1O2）、
  单位/普通英文词过滤、按受众给出 first_expand 与三文体 cross_genre 建议。
- terminology_engine.py audit：五类检查（variant_used / acronym_not_expanded / symbol_conflict /
  cross_file_inconsistent / unlocked_change），逐条定位 file:rpid，critical 未清零 exit=2。
- 共享核心：case 解析、源文结构化（事实清单/缩写/术语候选）、源文-改写逐段对齐。
- 诚实交付：骨架 result.json 防超时空手，validate 发布闸门，partial 如实降级。
