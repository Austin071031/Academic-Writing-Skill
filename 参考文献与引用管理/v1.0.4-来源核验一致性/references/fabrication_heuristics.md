# 编造/劣质条目的启发式特征清单

本地体检（verify_engine.py health_checks）只依据材料内字段做**确定性**检查。
检出 = suspicious（疑似），不是造假确证；确证需 Crossref 联网核验（--online）或人工复核。

## 1. DOI 不符合注册规则（check: doi_syntax）

Crossref 注册规则：`10.<4–9 位 registrant>/<后缀>`，后缀为可见 ASCII 非空白字符。
- 前缀不是 `10.` 开头（如 `doi: 1038/xxx`、直接写 URL 尾巴）。
- registrant 段不足 4 位或超过 9 位（如 `10.12/abc`）。
- 含空白、引号、尖括号、反斜杠等非法字符（如 `10.1038/ s41560`）。
- 有 DOI 字段但为空串/仅 "doi:"。
- 判定：suspicious；无 DOI 字段：insufficient_metadata（**不因此判假**——很多真实中文文献无 DOI）。

## 2. 年份不合理（check: year_plausibility）

- 晚于当前年份（如 2027、2030）——不可能已发表。
- 早于 1500——对现代期刊条目不合理。
- 年份字段无法解析为整数。
- 判定：suspicious；缺年份：insufficient_metadata。

## 3. 刊名与卷期页同时缺失（check: field_conflict）

- entry_type=journal_article 但 venue、volume、issue、pages **四项全空**。
  正规期刊著录极少如此，疑似拼接/编造条目（或解析失败的残缺条目）。
- 判定：suspicious。其他类型（book/conference 等）不适用本项。

## 4. 库内疑似重复录入（check: duplicate_title_in_library）

- 两条目归一化题名相似度 > 0.95（小写、去标点）**且第一作者相同**。
  常见于：同一文献被以中英文各录一遍、手滑复制多录。
- 判定：两条都记 suspicious（疑似重复录入）。注意：正文中两处引用若指向这两条，匹配裁决不受影响，
  但报告可疑条目表会列出。

## 5. 轻量著录笔误（check: title_ends_with_period）

- 题名著录以 `.`/`。` 结尾。多为导出/录入笔误，note 级提示，不降级条目总体判定。

## 组合信号（经验法则，供 Agent 阅读报告时参考）

- 多项同时命中（如 DOI 非法 + 年份 2031 + 卷期页全空）→ 编造概率显著升高，报告会在可疑条目表逐行列出。
- 单条目总体判定逻辑：任一检查 suspicious → 条目 overall=suspicious；仅缺题名 → insufficient_metadata；
  全部通过 → verified_internal（仅表示"本地自洽"，**不等于真实存在**）。

## 边界与诚实声明

- 真实但著录糟糕的条目（缺卷期、无 DOI 的老文献）会被误伤为 suspicious/insufficient_metadata——
  这是保守设计：宁可误报也不漏报，最终由联网核验或人工确认。
- verify_engine 的 suspicious 永远不会写成"confirmed_fake"；联网的 metadata_mismatch
  也只是"注册信息与本地著录不一致"，可能是著录错误而非编造。
