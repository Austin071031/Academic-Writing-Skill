# CHANGELOG

## v1.0.4（2026-11-19）
- 首版：长上下文登记簿与重复论述防护引擎 `dossier_engine.py`（纯标准库）。
  - `build`：定义句/缩写定义抽取（中文全称（英文, ABBR）、中文（ABBR）、
    english (ABBR)、X 是指/定义为/记为/即、is defined as/denote/let 六类模式）、
    结论句登记（带单位关键数值）、材料使用矩阵（2-gram Jaccard ≥0.15）与未用材料
    清单、术语/缩写首现表（使用早于定义=脱节候选）、图表 caption 登记。
  - `brief`：按目标章节相关性（2-gram Jaccard）排序、受 `--budget-chars` 约束的
    写作上下文摘要，五桶结构（定义/结论/未用材料/已用材料/caption），截断量如实
    记录——Agent 写作只读 brief 不通读全文。
  - `overlap`：四类复核——(a) 重复论述（句子 4-gram Jaccard ≥0.6）、
    (b) 重复结论（同主语[定义术语/化学式实体/2-gram≥0.25]+共享关键数值或
    4-gram≥0.3）、(c) 脱节（未定义全大写缩写 critical/warning 分级 + 悬空图表
    引用）、(d) 未用材料提醒（omissions 与 draft 最相关段落 2-gram Jaccard ≥0.1）；
    verdict: CLEAN / PASS_WITH_REMINDERS / HAS_ISSUES。
- 测试期修复的引擎缺陷：
  1. 定义 term 吞入前导动词（「是全固态电池」）→ 剥除前导动词；
  2. 化学式（Li6PS5Cl）与批次号（B7）被误判为未定义缩写 → 缩写候选限定全大写
     且 ≥2 字母，并按「前文是否出现过」分 critical/warning；
  3. 重复结论主语判据过窄（仅定义术语）→ 加入化学式实体与 2-gram 主语相似；
  4. 未用材料提醒按全文比 Jaccard 被长草稿稀释 → 改为与最相关段落比较。
- 合成案例端到端验证通过（见 evaluation/test_texts.md）：缺陷稿三项注入缺陷
  （重复结论/未定义缩写 HRTEM/重复论述）全部检出，干净稿 critical 零误报，
  validate_output PASS。
