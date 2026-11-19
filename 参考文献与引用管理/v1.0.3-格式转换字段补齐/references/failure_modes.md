# 失败模式库：基础 Agent 做格式转换时的典型错误

> 对照项来自"不加载 Skill 的基础 Agent"常见行为；本 Skill 的每一条规则对应至少一种失败模式。

## F1 丢 DOI / 卷期页在转换中静默消失

- 现象：BibTeX → GB/T 时模型重写条目，DOI 被省略，或 `5(3): 200-210` 只剩年份。
- 本 Skill 对策：转换全程字段级保留，`field_audit.json` 逐条核对 `fields_kept`，
  `convert_report.md` 第 3 节给出字段保留率，疑似丢失列入人工复核。

## F2 作者截断错误

- 现象：4 位作者不加 `等`/`et al` 全列；或反向——3 位作者误加 `et al`；
  中文条目误用 "et al"，英文条目误用 "等"。
- 对策：`format_specs/<style>.md` 声明 `max_authors` 与截断后缀；共享内核按语种加后缀；
  审计保留完整作者名单于 library.json 不丢信息。

## F3 中英文标点混用

- 现象：中文条目里半角逗号（`储能科学与技术, 2020, 9(2): 401-410.`）、
  英文条目里全角句号（`Nature Energy。`），或同一文献表两种风格并存。
- 对策：`normalize_punct` 按条目 language 分流；映射表见 `punctuation_rules.md`；
  DOI 受保护不被误转。

## F4 文献类型标识张冠李戴

- 现象：会议论文标 `[J]`、学位论文标 `[M]`、预印本标 `[C]`。
- 对策：类型标识表独立于代码（`format_specs/gbt_type_tags.md`），引擎读取资源文件解析；
  parse_library 的 entry_type 归一化是多格式一致的（bibtex/ris/endnote/cnki → 同一枚举）。

## F5 臆造缺失字段

- 现象：缺 DOI 时"编一个看起来像的"；缺页码时从记忆补 `pp. 1-10`；缺年份写 `2021`。
- 对策：**红线**。缺字段一律 `not_provided` + "材料未提供，不得臆造补齐"；
  仅允许同题同年同类型重复条目的字段互补（`copied_from_R00X`，可溯源）；
  联网探测 5 秒超时、失败记录 `unverified`，绝不把未验证数据写进条目。

## F6 名字形转换臆造中间名

- 现象：`Smith J` 被写成 `Smith J R`（材料只给了名首字母 J），或 `John Smith` 与 `Smith, John` 混排。
- 对策：`western_to_gbt` 仅取材料中实际出现的名首字母；无逗号形式按"末词为姓"处理；
  不确定的姓名列入 manual_confirmations。

## F7 预印本被"升级"为期刊条目

- 现象：同题的 arXiv 预印本与期刊版并存时，把期刊的卷期页/DOI 抄给预印本。
- 对策：跨条目互补要求 entry_type 一致（或一方为 misc）**且年份一致或缺失**；
  年份冲突即拒绝互补（见 worked_example R003）。
