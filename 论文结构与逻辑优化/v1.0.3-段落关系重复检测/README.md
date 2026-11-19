# paragraph-redundancy-map（段落关系与重复内容）v1.0.3

论文结构与逻辑优化 Skill：**主攻段落关系与重复内容**，六维普查兜底覆盖。

## 它解决什么问题

基础 Agent 审"查重/压缩"时只能给"减少重复表述"这类空话。本技能把重复与段落衔接做成**可机检的映射**：

- 段落重复对表：全部段落两两字符 3-gram Jaccard，≥0.55 判重复（同章相邻→合并；跨章→删冗余侧+交叉引用，保留角色更核心者），0.30–0.55 判近似重复（差异化改写或合并）；
- 结构性呼应识别：摘要↔引言、结论↔摘要的高重叠单独标注"点题 vs 冗余"，confidence≤0.6 交人工裁决；
- 句子级跨章近重复（≥0.80）：比段落级更细，抓"同一句话在两章各说一遍"；
- 衔接分析：同章相邻段话题跳变无过渡（add_transition）、段首回指悬空（"如前所述"却前 3 段无内容词重叠）；
- 拆分候选：≥400 字符且内部句子两两平均相似度<0.03 的多话题混杂段，给出建议拆分句界；
- 统计：重复对数、涉及段落数、冗余字符估算（较短段字符数之和）。

每条问题定位到 **章节 › 段落 › 句子** 并附原文锚点与 9 类编辑动作之一（move/merge/split/narrow/qualify/add/add_transition/add_limitation/reorder），输出**编辑计划而非改写稿**。

## 快速开始

```bash
# 平台环境（/input 有 case.json/task.md/稿件）
python3 scripts/init_result.py
python3 scripts/inspect_case.py --work /app/work
python3 scripts/parse_manuscript.py --work /app/work
python3 scripts/six_scan.py --work /app/work
python3 scripts/redundancy.py --work /app/work
python3 scripts/report_builder.py --work /app/work --out /app/output \
  --focus redundancy --skill "paragraph-redundancy-map v1.0.3"
# → 人工/Agent 复核 diagnosis_report.md（删误报/补漏报/定优先级）
python3 scripts/assemble_result.py --work /app/work --out /app/output \
  --skill "paragraph-redundancy-map v1.0.3" --status success
python3 scripts/validate_output.py --out /app/output --work /app/work
```

完整说明见 [docs/USAGE.md](docs/USAGE.md)；最小调用示例见 [examples/minimal_example.md](examples/minimal_example.md)。

## 目录

- `SKILL.md` — 技能本体（Agent 工作流）
- `scripts/` — 纯标准库 Python3 管线（零依赖；PDF 抽取可选依赖 pdftotext）
- `references/` — 判据、分类、标注示例、误报模式
- `docs/USAGE.md` — 使用与方法说明、失败处理、自查
- `evaluation/` — 评分自查表、合成测试文本
- `examples/` — 最小调用示例（示意输出已标注）

## 兼容与限制

Python ≥ 3.8，无第三方依赖；稿件格式 md/txt/tex/docx/pdf。阈值集中于 `scripts/scanutil.py:THRESH`，可复核可调。语义级同义复述（无共同 n-gram）漏检需人工复核（见 references/failure_modes.md）。
