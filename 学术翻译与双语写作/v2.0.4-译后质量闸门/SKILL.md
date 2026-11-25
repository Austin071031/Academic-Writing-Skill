---
name: translation-qa-gate
description: 学术翻译技能（v2 迭代·主攻“结果正确性”：译后质量闸门）。在句段级翻译管线（父辈 v1.0.1 数字台账）上增加 qa_gate.py 一次三门机检：①数字忠实（缺失/增译/改动三档/单位差异，跨语言量级归一）②引用与语义边界（引用标记三形态多重集比对、否定范围丢失、可能性/约数/限定强度丢失、语气升格、增译数字去重分工）③缩写一致性（首现定义保留检查）；输出按严重度排序的统一修复清单 qa_report.json（rank/id/seg_id/修订指令），高严重度必须清零方可交付。当用户要求翻译结果正确性可证明、译后逐条可修复时使用；输入 /input 下稿件与 case.json，输出 /app/output 下 translation_full.md、bilingual.md、qa_report.json、number_audit.json、boundary_audit.json、audit_annotated.md、report.md、result.json。
---

# 译后质量闸门 · 学术翻译 Skill（v2.0.4，父辈 v1.0.1）

## 用途与适用条件

整篇学术稿件句段级翻译。**本版核心增量：把三类最高价值机检合并为一道交付前闸门**——数字、引用/语义边界、缩写一致性一次运行、去重、按严重度排序出统一修复清单，高严重度清零才允许交付。评分“结果正确性 15 分”直接对应：术语、数字、单位、引用、否定与限定条件与原文一致，无凭空补写。

适用：对正确性要求高的整篇翻译。不适用：纯数据无正文文件（如实降级）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、稿件；工作目录 `/app/work`；交付 `/app/output`。
- 预算：64 次模型请求 / 900 秒。译文追加写入 translations.jsonl，随时可组装。
- 本目录即技能根：`scripts/`、`references/`、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线

1. **高严重度不清零不交付**：qa_report 中高严重度（数字缺失/改动/增译、引用缺失/新增、否定丢失、语气升格）未处置前 status 不得为 success。
2. **数字零臆造 / 引用标记原样**（父辈边界规则）。
3. **不静默跳过句段**：未译句段以【缺译】标记并计 uncertainty。

## 标准工作流（严格按序执行）

```bash
SKILL_DIR=/skills/weekly-skill   # 平台安装路径；本地调试用本目录
W=/app/work; O=/app/output; mkdir -p $W $O
S=$SKILL_DIR/scripts

python3 $S/init_result.py
python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W
python3 $S/segment_builder.py --work $W
python3 $S/number_engine.py ledger --work $W    # 数字台账（译前约束）
python3 $S/boundary_engine.py index --work $W   # 引用/语气索引（译前约束）
```

**第 6 步（Agent 翻译）**：打开 `work/source_for_translation.md` 分批翻译（每批 20–40 句段），追加写 `work/translations.jsonl`：
- 数字对照台账；引用标记逐字符保留；否定/可能/约数/限定等强译出；禁止增译。
- 预算兜底：请求用满 40 次仍未译完，进第 7 步按缺译交付 partial。

```bash
python3 $S/assemble_translation.py --work $W --out $O   # 7) 组装纯译文+双语对照
python3 $S/qa_gate.py --work $W                         # 8) 质量闸门（本版核心）
cat $W/qa_report.json    # 重点：fix_list 按 rank 逐条处置
```

**第 9 步（Agent 修复循环，禁止跳过）**：
1. 按 qa_report.fix_list 的 rank 顺序处置：真错→修订译文追加 translations.jsonl；误报→findings.json 标“已驳回”写理由（常见误报见 references/failure_modes.md）。
2. 重跑第 7、8 步确认高严重度清零；最多两轮，仍有残留则 status=partial 并在 uncertainty 列明。
3. 词表未覆盖的否定/限定句式（“未能/难以”）：写 `work/custom_lexicon.json` 扩展后重跑闸门。

```bash
# 10) 报告 + 契约组装 + 闸门 + 预览
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "translation-qa-gate v2.0.4"
python3 $S/assemble_result.py --work $W --out $O --skill "translation-qa-gate v2.0.4" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理

| 情况 | 处置 |
|-|-|
| 无稿件候选 / 空文件 | 保留骨架 status=failed，exceptions 记录 |
| PDF 无文本层 | exceptions 记录；上标引用可能丢失，uncertainty 标注 |
| 引用格式异常（[?]/断链） | exceptions 记录；按原文形态比对，不擅自修复源文 |
| 语气词表未覆盖 | custom_lexicon.json 扩展重跑；记入 change_log |
| 高严重度两轮未清零 | status=partial，uncertainty 逐条列明残留 |
| 超长稿件 / 脚本异常 | 分批 partial 兜底；脚本读 stderr 修复重跑（幂等） |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `translation_full.md` / `bilingual.md` | 纯译文 / 双语对照 |
| `qa_report.json` | 统一修复清单：rank/severity/dimension/seg_id/修订指令 + 分维度统计 |
| `number_audit.json` / `boundary_audit.json` | 数字比对表 / 引用与边界核对表 |
| `audit_annotated.md` | ⚠ 标注稿（问题句段三联对照） |
| `result.json` | 契约结果：case_id、status、evidence_map、change_log、uncertainty |

## 关键方法（详见 references/）

- `references/qa_gate_rules.md`：三门检查项、去重分工、严重度定义、清零纪律。
- `references/number_rules.md`：数字归一与改动分级（父辈机制）。
- `references/failure_modes.md`：误报来源与复核要点。

## 限制

- 语气/否定核对基于可扩展词表；句式承担的语义由 Agent 复核兜底。
- 闸门保证“与原文一致”，不判断原文本身的科学正确性。
