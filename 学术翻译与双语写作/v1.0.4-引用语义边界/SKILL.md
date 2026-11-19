---
name: citation-semantic-boundary
description: 学术翻译技能（主攻“引用保留与语义边界·边界清”）。译前建立引用与语气索引（逐句段引用标记清单：数字型 [1]、著者-年型 (Zhang et al., 2023) 与叙述型 Zhang et al. (2023)；六类语气/否定/限定标记；参考文献条目逐条登记），译后逐句段核对：引用标记多重集一致（缺失/新增=高）、参考文献条目原样保留、否定范围丢失（no/not↔不/无/未=高）、可能性/表明类/约数/限定条件强度丢失（中）、语气升格（源无确定性表述而译文出现“证明/必然/完全”=高）、增译数字（高）；产出 ⚠ 标注稿供作者复核。适用于引用密集的论文翻译与双语写作，尤其需要守住否定范围、因果强度与模糊限制语的场景；不适用于无引用非学术文本（引擎如实零发现）。输入 /input 下稿件与 case.json，输出 /app/output 下 translation_full.md、bilingual.md、boundary_audit.json、citation_index.json、audit_annotated.md（⚠ 标注稿）、report.md、result.json。
---

# 引用保留与语义边界 · 学术翻译 Skill

## 用途与适用条件

对完整学术稿件做句段级翻译，主攻题面“边界清”：引用与归属完整保留，增译、省译、否定范围、因果强度和模糊限制语保持原意，不出现作者没说过的结论。机制：脚本建**引用/语气双索引**并做译后**逐句段比对 + ⚠ 标注稿**（秒级），Agent 只做翻译与复核。

适用：引用密集、论断强度敏感的论文翻译。不适用：无引用非学术文本（引擎零发现，不构成失败）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、稿件；工作目录 `/app/work`；交付 `/app/output`。
- 预算：64 次模型请求 / 900 秒。译文追加写入 translations.jsonl，随时可组装。
- 本目录即技能根：`scripts/`、`references/`、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线

1. **引用标记原样**：[1] 不译不挪；(Zhang et al., 2023) 保持作者-年份（全角括号允许、内容不动）；参考文献条目不译不删不改顺序。
2. **强度不漂移**：可能/表明/约/仅/不等限定语等强译出；原文没有的确定性表述（证明/必然/完全/所有）译文不得出现；作者没说的结论一字不加。
3. **不静默跳过句段**：未译句段以【缺译】标记并计 uncertainty。

## 标准工作流（严格按序执行）

```bash
SKILL_DIR=/skills/weekly-skill   # 平台安装路径；本地调试用本目录
W=/app/work; O=/app/output; mkdir -p $W $O
S=$SKILL_DIR/scripts

python3 $S/init_result.py                       # 1) 兜底骨架
python3 $S/inspect_case.py --work $W            # 2) 案例侦察（方向/形态）
python3 $S/parse_manuscript.py --work $W        # 3) 结构解析（稳定 ID）
python3 $S/segment_builder.py --work $W         # 4) 句段切分 + 受保护片段
python3 $S/boundary_engine.py index --work $W   # 5) 引用/语气双索引（译前约束）
cat $W/citation_index.json  # 重点：各句段引用标记与语气标记清单、参考文献条目数
```

**第 6 步（Agent 翻译）**。打开 `work/source_for_translation.md` 分批翻译（每批 20–40 句段），追加写 `work/translations.jsonl`：
- 对照 citation_index.json：引用标记逐字符保留在对应论断处；et al. 保留不译。
- 语气等强对照表见 references/boundary_rules.md：may→可能/或、suggest→表明/提示、
  approximately→约、only→仅/只、no/not→不/无/未（**否定词一个都不能丢**）。
- 禁止增译：不补充原文没有的数据、机理猜测与文献。
- 预算兜底：请求用满 40 次仍未译完，进第 7 步按缺译交付 partial。

```bash
python3 $S/assemble_translation.py --work $W --out $O   # 7) 组装纯译文+双语对照
python3 $S/boundary_engine.py audit --work $W           # 8) 边界机检 + ⚠ 标注稿
cat $W/boundary_audit.json    # 重点：citation_fidelity 与各句段 issues
```

**第 9 步（Agent 复核与修订，禁止跳过）**：
1. **逐条处置 findings**：成立者把修订译文追加到 translations.jsonl（同 seg_id 覆盖），重跑 7、8。
2. **删误报**：常见误报见 references/failure_modes.md（同义限定词未在词表、否定由句式承担如“未能”“难以”）；驳回须在 findings.json 写明理由，必要时在 work 下补充 custom_lexicon.json 扩展词表后重跑。
3. **⚠ 标注稿确认**：audit_annotated.md 供作者快速复核；确认全部处置完毕。

```bash
# 10) 报告 + 契约组装 + 闸门 + 预览
python3 $S/report_builder.py --work $W --out $O --focus boundary --skill "citation-semantic-boundary v1.0.4"
python3 $S/assemble_result.py --work $W --out $O --skill "citation-semantic-boundary v1.0.4" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理

| 情况 | 处置 |
|-|-|
| 无稿件候选 / 空文件 | 保留骨架 status=failed，exceptions 记录 |
| PDF 无文本层 | exceptions 记录；上标引用可能丢失，uncertainty 标注 |
| 上标引用（Word/PDF ¹²³） | 文本层无上标语义：按 [n] 形态缺失处理，uncertainty 标注人工核对 |
| 引用格式异常（[?]、断链、重复编号） | 如实记录 exceptions；比对按原文形态进行，不擅自修复源文 |
| 参考文献无编号（著者-年份制） | 按整段/逐条登记条目数与首 60 字符指纹比对 |
| 语气词表未覆盖学科惯用语 | custom_lexicon.json 扩展后重跑；记录 change_log |
| 超长稿件 / 脚本异常 | 分批翻译 partial 兜底；脚本读 stderr 修复重跑（幂等） |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `translation_full.md` / `bilingual.md` | 纯译文 / 双语对照（结构原位） |
| `citation_index.json` | 译前引用/语气双索引（逐句段清单+参考文献条目） |
| `boundary_audit.json` | 逐句段比对结果；citation_fidelity 引用保留率 |
| `audit_annotated.md` | ⚠ 标注稿：问题句段原文/译文/机检意见三联对照 |
| `report.md` / `findings.json` / `edit_plan.json` | 质量报告与修订清单 |
| `result.json` | 契约结果：case_id、status、evidence_map、change_log、uncertainty |

## 关键方法（详见 references/）

- `references/boundary_rules.md`：引用三形态归一、六类语气词表与等强对照、升格判定、
  增译数字与数字引擎的去重分工。
- `references/failure_modes.md`：误报来源与复核要点。
- `references/worked_example.md`：完整标注示例（合成，非正式案例）。

## 限制

- 语气核对基于词表命中：否定/限定由复杂句式承担时（“未能”“并非…而是”）可能误报，
  由 Agent 复核兜底，词表可扩展。
- 引用-论断的语义相关性（引文是否支持该论断）超出本版本范围。
- 上标引用的语义恢复依赖文本层质量，PDF 抽取损失时如实降级。
