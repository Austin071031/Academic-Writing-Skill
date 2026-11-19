# 完整标注示例（合成案例，非正式测试案例）

> 以下输入与输出均为合成演示，用于说明接口与标记语法，不代表正式案例结果。

## 合成输入（节选）

`prior_work.md`（role_guess=prior_work）：

> 申请人已发表 Joule 期刊论文 1 篇（2023），首次报道两性离子界面修饰策略，器件效率 23.4%。
>
> 已获授权发明专利 ZL202210123456.7 一项，涉及界面修饰层配方与涂布工艺。
>
> 已建立 200 m² 钙钛矿组件中试线，掌握狭缝涂布与溶剂工程放大工艺。团队现有博士生 5 名。

## 管线中间产物

- `fact_ledger.json`：F0034=pub_mention Joule（F3-P003）、F0038=pub_mention ZL202210123456.7
  （F3-P005）、F0026=number 200 m²（F3-P007）、F0035=number 5 名（F3-P007）……
- `feasibility_engine.py seed` → `evidence_chain_seed.json`（机选初稿）：

```json
{"row_id": "R001", "capability": "申请人已发表 Joule 期刊论文 1 篇（2023），首次报道两",
 "evidence_fids": ["F0034"], "sources": [{"file_id": "F3", "pid": "F3-P003"}],
 "relation_to_project": ""}
```

- Agent 第 6 步审定：填关系列、删无关行，另存 `evidence_chain.json`：

```json
{"row_id": "R001", "capability": "两性离子界面修饰方法学（Joule 论文）",
 "evidence_fids": ["F0034"], "sources": [{"file_id": "F3", "pid": "F3-P003"}],
 "relation_to_project": "界面修饰分子设计能力直接支撑研究内容（一）偶极取向调控与目标一"}
```

## 章节稿节选（work/sections/07_研究基础与可行性.md）

```markdown
# 研究基础与可行性

申请人已发表 Joule 期刊论文〔F0034〕，建立了两性离子界面修饰的方法学基础；
已获授权发明专利一项〔F0038〕，配方与涂布工艺受知识产权保护，支撑研究内容（二）放大制备。

平台方面，已建立 200 m² 钙钛矿组件中试线〔F0026〕，掌握狭缝涂布工艺，
团队现有博士生 5 名〔F0035〕，具备开展界面放大验证的平台条件与团队保障。

本课题拟在上述中试线上开展组件放大验证，预期完成 3 轮工艺迭代〔拟〕。
```

## 审计结果（合规版）

- feasibility_engine audit：体貌规则 0 命中（已完成段 completed、〔拟〕段 planned）；
  成果断言全部带〔F〕；evidence_chain.json 关系列齐全；可行性信号齐备 → findings=0。
- source_audit：Joule、ZL…、200 m²、5 名全部命中台账 → 0 high。

## 反例（注入缺陷时机检命中）

| 注入缺陷 | 预期命中 |
|-|-|
| 「本课题下一阶段已完成放大效率复测〔拟〕」 | aspect_violation_planned_as_done（high） |
| 「申请人拟将相关成果整理投稿至 Joule 期刊〔F0034〕」（材料记载已见刊） | aspect_violation_done_as_planned（medium） |
| 「申请人发表高水平论文多篇，获授权专利数项」（无〔F〕） | unsourced_achievement（high） |
| evidence_chain.json 某行 relation_to_project="" | chain_incomplete（medium） |
| 删除 evidence_chain.json 只留 seed | chain_incomplete（low：未生成审定版） |
| 整节只列成果、无 平台/团队/可行 等词 | feasibility_missing（low） |
