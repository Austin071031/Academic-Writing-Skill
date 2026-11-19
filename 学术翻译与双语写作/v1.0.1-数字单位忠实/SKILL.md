---
name: translation-number-fidelity
description: 学术翻译技能（主攻“事实与数字·数字实”）。整篇翻译前先由脚本建立数字台账（每个句段的全部数字：值/单位/量级/原文形态），译后逐句段双向比对：源有译无（缺失）、译有源无（增译数字）、值不等（区分疑似四舍五入/数字笔误/实质改动）、单位形式差异；跨语言表达（万/亿/千/百↔thousand/million/billion、千分位、科学计数、%与‰）按归一值等值判定，只允许等值换算、不允许顺手改整。适用于含大量实验数据的论文翻译（效率、电压、温度、样本量、年份、统计口径），英译中与中译英均可；不适用于无数字内容文本（引擎如实报告零发现）。输入 /input 下稿件与 case.json，输出 /app/output 下 translation_full.md、bilingual.md、number_ledger.json（数字台账）、number_audit.json（逐句段比对表）、report.md、result.json。
---

# 数字与单位忠实校对 · 学术翻译 Skill

## 用途与适用条件

对完整学术稿件做句段级翻译，主攻题面“数字实”：数字、单位、量级、范围、年份、统计口径原样落地，不被四舍五入、单位错配或“顺手改成整数”。机制：脚本建立**数字台账**并做译后**逐值双向比对**（机械劳动秒级），Agent 只做翻译与复核。

适用：数据密集的实验类论文翻译（双语向均可）。不适用：纯文字无数据稿件（引擎报告零发现，不构成失败）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、稿件；工作目录 `/app/work`；交付 `/app/output`。
- 预算：64 次模型请求 / 900 秒。译文追加写入 translations.jsonl，随时可组装部分结果。
- 本目录即技能根：`scripts/`、`references/`、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线

1. **数字零臆造**：译文每个数字必须能在源句段找到等值对应；找不到的由引擎判“增译数字”（高严重度），不得保留。
2. **不静默跳过句段**：未译句段以【缺译】标记并计 uncertainty。
3. **等值换算才允许**：万/亿↔million/billion 只允许数学等值（120万=1.2 million），有效数字位数与单位符号不得擅改；任何换算在 number_audit 中留痕。

## 标准工作流（严格按序执行）

```bash
SKILL_DIR=/skills/weekly-skill   # 平台安装路径；本地调试用本目录
W=/app/work; O=/app/output; mkdir -p $W $O
S=$SKILL_DIR/scripts

python3 $S/init_result.py                       # 1) 兜底骨架
python3 $S/inspect_case.py --work $W            # 2) 案例侦察（翻译方向/交付形态）
python3 $S/parse_manuscript.py --work $W        # 3) 结构解析（稳定 ID）
python3 $S/segment_builder.py --work $W         # 4) 句段切分 + 受保护片段
python3 $S/number_engine.py ledger --work $W    # 5) 数字台账（译前约束）
cat $W/number_ledger.json   # 重点：每个含数字句段的值/单位/原文形态
```

**第 6 步（Agent 翻译，受台账约束）**。打开 `work/source_for_translation.md` 分批翻译（每批 20–40 句段），追加写 `work/translations.jsonl`（每行 `{"seg_id":…,"translation":…}`）：
- 对照 number_ledger.json：每个数字的值、单位、有效位数原样落地；〔保留:…〕片段逐字符保留。
- 中英文数字表达差异只允许等值换算："1.2 million"→"120万"（或保留 1.2 million）；
  "约为120万篇"→"approximately 1.2 million"。**禁止** 23.4%→23%、0.873→0.87、"over 25%"→"25%"。
- 范围（3.8%–25%）、±误差（±0.3%）、比较级（over/at least/no more than）一并保留。
- 预算兜底：请求用满 40 次仍未译完，立即进第 7 步按缺译交付 partial。

```bash
python3 $S/assemble_translation.py --work $W --out $O   # 7) 组装纯译文+双语对照
python3 $S/number_engine.py audit --work $W             # 8) 数字双向比对
cat $W/number_audit.json    # 重点：entries 各句段 issues 与 summary.fidelity
```

**第 9 步（Agent 复核与修订，禁止跳过）**：
1. **删误报**：对照原文复核每条 finding；常见误报见 references/failure_modes.md（上下文关键词中的年份、编号被当数据、等值但写法不同被判形式差异）。驳回须在 findings.json 写明理由。
2. **修译文**：成立的违规把修订译文追加到 translations.jsonl（同 seg_id 覆盖），重跑第 7、8 步确认清零。
3. **定性质**：对“疑似四舍五入/笔误”条目判断是否源文本身如此（源文即 23% 则非问题）。

```bash
# 10) 报告 + 契约组装 + 闸门 + 预览
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "translation-number-fidelity v1.0.1"
python3 $S/assemble_result.py --work $W --out $O --skill "translation-number-fidelity v1.0.1" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理

| 情况 | 处置 |
|-|-|
| 无稿件候选 / 空文件 | 保留骨架 status=failed，exceptions 记录 |
| PDF 无文本层 / 抽取为空 | exceptions 记录；status≤partial |
| 稿件无数字 | ledger/audit 如实报告零发现，不构成失败 |
| 无法归一的特殊记数（罗马数字、中文大写） | 不抽取，uncertainty 标注“该形态未纳入机检，人工核对” |
| 数字歧义（"3.8" 既为数据又为版本号） | audit 候选交第 9 步人工裁决 |
| 超长稿件 | 分批翻译；预算过半优先数据密集章节，其余缺译 partial |
| 脚本异常 | 读 stderr 修复重跑（幂等）；不能修则保留已有产物 partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `translation_full.md` / `bilingual.md` | 纯译文 / 双语对照（结构原位保留） |
| `number_ledger.json` | 数字台账：逐句段全部数字的值/单位/原文形态（译前约束、译后依据） |
| `number_audit.json` | 双向比对表：matched/missed/added 逐句段列出，summary.fidelity 忠实率 |
| `report.md` / `findings.json` / `edit_plan.json` | 质量报告与机读修订清单 |
| `result.json` | 契约结果：case_id、status、evidence_map、change_log、uncertainty、stats |

## 关键方法（详见 references/）

- `references/number_rules.md`：归一规则（万/亿/million、千分位、科学计数、%与‰）、
  改动分级判据（四舍五入/笔误/实质改动）、引用内数字屏蔽规则。
- `references/failure_modes.md`：误报来源与复核要点。
- `references/worked_example.md`：完整标注示例（合成，非正式案例）。

## 限制

- 归一覆盖阿拉伯数字+常见单位与量级词；中文大写数字、罗马数字、分数拼写（two thirds）
  不纳入机检，列入 uncertainty 由人工核对。
- “疑似四舍五入”为数值判据（末位级差异），最终定性依赖 Agent 复核源文写法。
- 数值合理性（如 23.4% 是否物理可信）不在机检范围；本 Skill 核对的是“与原文一致”。
