# conclusion-boundary-check（结论边界与表述尺度核验）v1.0.4

论文结构与逻辑优化 Skill：**主攻结论边界与表述尺度**，六维普查兜底覆盖。

## 它解决什么问题

基础 Agent 审稿件结论时给出的大多是"避免夸大"的通用提醒。本技能把"结论是否超出数据与实验条件"做成**可机检的核验**：

- 数字溯源表：结论/摘要中每个数字逐条在方法/实验/结果/讨论章做三层匹配——逐字命中 ok / 数值相等格式不同（0.873 vs 87.3%，提示人工）/ 相对差 ≤5% 且可舍入得到（疑似四舍五入或笔误）/ 完全无匹配（无源数字，high）；年份与图表编号自动剔除；
- 摘要-结论一致性：同语境句对（内容词 Jaccard≥0.4）数字集合比对，列出"摘要 65.2%、结论 65.8%"类不符；
- 因果三档裁决：结论因果句 × 方法实验章设计词（对照/随机/消融）× 正文相关性词 → supported / overreach（把相关当因果）/ unverifiable；
- 推广范围比对：结论"所有体系/通用/universal"类范围词 × 方法实验章实际测试条件枚举 → 推广超界；
- 限制说明审计：局限性表述的缺失/位置（致谢附录）/充分性（仅一句且无量化边界）三态裁决。

每条问题定位到 **章节 › 段落 › 句子** 并附原文锚点与 9 类编辑动作之一（move/merge/split/narrow/qualify/add/add_transition/add_limitation/reorder），输出**编辑计划而非改写稿**。

## 快速开始

```bash
# 平台环境（/input 有 case.json/task.md/稿件）
python3 scripts/init_result.py
python3 scripts/inspect_case.py --work /app/work
python3 scripts/parse_manuscript.py --work /app/work
python3 scripts/six_scan.py --work /app/work
python3 scripts/boundary_audit.py --work /app/work
python3 scripts/report_builder.py --work /app/work --out /app/output \
  --focus conclusion_boundary --skill "conclusion-boundary-check v1.0.4"
# → 人工/Agent 复核 diagnosis_report.md（删误报/补漏报/定优先级）
python3 scripts/assemble_result.py --work /app/work --out /app/output \
  --skill "conclusion-boundary-check v1.0.4" --status success
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

Python ≥ 3.8，无第三方依赖；稿件格式 md/txt/tex/docx/pdf。溯源容差与一致性阈值集中在 `scripts/boundary_audit.py` 顶部常量（APPROX_TOL / ECHO_JACCARD），可复核可调。数字语义出处（如来自被引文献）需人工复核（见 references/failure_modes.md）。
