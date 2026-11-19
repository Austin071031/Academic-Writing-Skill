# 评分对齐自评（scoring_sheet.md）

评分维度：实际效果40 / 使用增益25 / 创新增益15 / 可靠体验10 / 生态贡献10（目标≥80）。

## 实际效果（40）

| 题面要求 | 实现 | 证据 |
|-|-|-|
| 论断与具体文献绑定 | bind：四种样式解析到 entry_ids；unbound=critical | claim_bindings.json；合成测试 P001 unbound / P002 bound |
| 发现"引用了不存在文献" | numeric 越界 / latex key 不存在 / author_year 未匹配 | citation_audit (a) 节；负例 [5] 检出 |
| 发现"引用了文献但结论被改写" | 语气阶梯比对 → overstated / negation_flip 候选 | 负例「完全解决」vs 材料「仍是挑战」检出 overstated+negation_flip |
| 补齐或标记存疑引用 | missing_citation 段 + top3 候选条目；unverified 逐值列证 | citation_audit (b)(d) 节；批注稿 ⚠ 标出 |
| 数值核验 | verbatim/derived/unverified + 遮蔽图表/章节/年份/化学式 | 正例 3.2 判 verbatim、第1章/目标句不误报 |
| GB/T 7714-2015 渲染 | render_refs + 编号连续与双向一致交叉核对 | references.md；references_audit.json sequential=true |
| 术语缩写统一 | 判据驱动 Agent 流程（citation_rules §5） | SKILL Phase 3 / docs USAGE 清单 |

## 使用增益（25）

- Phase 0-5 与 v1.0.0 模板同构，与共享脚本零接口冲突；每步命令可复制粘贴；
- 输出双份（机器 JSON + 人读 MD + ⚠ 批注稿），作者与评审各取所需；
- 异常处置表 12 类，常见坑均有指向性处置。

## 创新增益（15）

- 语气强度量化阶梯（L1-L4）+ 语义材料句匹配（关键词+数值加权），把"结论被改写"
  从人工通读变成确定性候选列表；
- 数值遮蔽体系（图表号/章节号/年份/化学式/型号）使"逐值核对"在非结构化稿上可用；
- 漏引检测自带豁免（可溯源自有数据段）+ top3 推荐，避免满篇误报。

## 可靠体验（10）

- 纯标准库、无网络；bind/verify 退出码 1 显式表达 critical，Agent 可脚本化处理；
- validate_output 硬闸门（编号连续、双向一致、evidence_map 非空）防"假装成功"；
- 红线 3 条 + 失败模式 12 类兜底。

## 生态贡献（10）

- 引擎 subcommand 独立可复用（其他版本可直接 `import` 或子进程调用）；
- 判据文档 references/citation_rules.md 与引擎逐条对应，可审计；
- 合成测试 `_test/input`（ch1_intro / ch1_bad / refs.bib / facts / notes_interface）
  可直接复用为后续版本回归集。
