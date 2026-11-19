# 自查评分表（对照赛题评分维度）

> 交付前逐项自查；任何一项答“否”须修复或如实降级 status。

## 实际效果（40）

- [ ] 整篇译出：stats.coverage = 1.0（否则 status=partial 且缺译已标记）
- [ ] 输出形态：translation_full.md（纯译文）与 bilingual.md（双语对照）均交付
- [ ] 术语正确一致：glossary.json 已审定；term_audit.summary.violations = 0
        或剩余项均已驳回并写明理由
- [ ] 数字/单位/引用原样：受保护片段未被改动（segments.json protected 对照）
- [ ] 完整性：章节、图表题注、脚注、公式、参考文献条目全部保留
- [ ] 可核验：evidence_map 逐句段含原文/译文对照；term_audit 逐术语可回溯

## 使用增益（25）

- [ ] 术语表审定 + 逐句段核对替代人工逐处查找译名漂移
- [ ] 缺译/漂移自动定位到句段，后编辑无需通读比对
- [ ] 修订闭环可重跑验证（audit 清零）

## 创新增益（15）

- [ ] 三类来源术语候选 + 锁定-核对闭环（基础 Agent 无此机制）
- [ ] 学科歧义与 declared_variants 显式管理
- [ ] 术语表作为可复用资产沉淀（glossary.json）

## 可靠体验（10）

- [ ] SKILL.md 工作流可逐字执行；命令全部实测通过
- [ ] 异常表覆盖：无稿件/PDF 降级/术语表冲突/语向不符/超长稿件/脚本异常
- [ ] init 骨架 + 追加式译文，中断可交付诚实 partial

## 生态贡献（10）

- [ ] README/USAGE/方法/误报/示例/CHANGELOG/GITHUB_URL 齐备
- [ ] 脚本纯标准库，他人可直接复用
- [ ] 示例明确标注“示例，非正式案例结果”
