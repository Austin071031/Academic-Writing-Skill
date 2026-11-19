---
name: bilingual-alignment-guard
description: 学术翻译技能（主攻“双语对齐·对得齐”）。把原文切成带稳定 ID 的句段（章节标题/正文句/图表题注/脚注/公式/参考文献条目分别处理），译前生成对齐计划与结构不变量（图表编号集合、脚注标记、公式块数、参考文献条目数），译后逐句段核对：缺译、未知句段 ID（疑似新增/串段）、长度比例异常（疑似漏译从句或增译）、图表编号与脚注标记在译文中的集合一致性；自动生成段首带 〔PID〕 的双语对照稿，译者可逐段修改而不破坏结构。适用于需要中英对照修改流程的整篇论文翻译、学位论文双语稿、投稿翻译；不适用于只需纯译文且无对照需求的场景（仍可用，对照稿自动附带）。输入 /input 下稿件与 case.json，输出 /app/output 下 bilingual.md（双语对照）、translation_full.md、alignment.json（逐句段对齐状态）、align_audit.json、report.md、result.json。
---

# 句段级双语对齐 · 学术翻译 Skill

## 用途与适用条件

对完整学术稿件做句段级翻译并交付**可逐段修改的双语对照稿**，主攻题面“对得齐”：原文与译文句段一一对应，段落顺序、图表编号、题注与脚注对应关系完整保留。机制：脚本建立**对齐计划与结构不变量**并做译后**全覆盖核对**，Agent 只做翻译与复核。

适用：需要双语对照修改流程的整篇翻译。不适用：纯译文需求（仍附带对照稿，无额外成本）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、稿件；工作目录 `/app/work`；交付 `/app/output`。
- 预算：64 次模型请求 / 900 秒。译文按句段追加写入 translations.jsonl，随时可组装。
- 本目录即技能根：`scripts/`、`references/`、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线

1. **不合并、不拆分、不增删句段**：一个 seg_id 对一条译文；确需合译/分译的，译在一个 seg_id 下并在另一条写 `（并入 <seg_id> 合译）`，由 Agent 复核确认。
2. **结构元素原位**：图表编号、脚注标记、公式、参考文献条目原位保留；公式与文献条目不译不删。
3. **缺译不静默**：未译句段以【缺译】标记并计 uncertainty，禁止删除源句段凑整齐。

## 标准工作流（严格按序执行）

```bash
SKILL_DIR=/skills/weekly-skill   # 平台安装路径；本地调试用本目录
W=/app/work; O=/app/output; mkdir -p $W $O
S=$SKILL_DIR/scripts

python3 $S/init_result.py                       # 1) 兜底骨架
python3 $S/inspect_case.py --work $W            # 2) 案例侦察（方向/形态）
python3 $S/parse_manuscript.py --work $W        # 3) 结构解析（稳定 ID）
python3 $S/segment_builder.py --work $W         # 4) 句段切分（6 类）
python3 $S/align_engine.py plan --work $W       # 5) 对齐计划 + 结构不变量
cat $W/alignment_plan.json  # 重点：invariants（图表编号/脚注/公式/文献条目数）
```

**第 6 步（Agent 翻译）**。打开 `work/source_for_translation.md` 分批翻译（每批 20–40 句段），追加写 `work/translations.jsonl`：
- 严格逐句段：每个待译 seg_id 一条译文；`〔不译·原样保留〕` 行不译不删。
- 图表题注整句翻译但编号原样（"Figure 1."→"图1."）；脚注标记 `[^1]` 逐字符保留。
- 从句较多的长句不得漏译从句；不得加入原文没有的解释性内容。
- 预算兜底：请求用满 40 次仍未译完，进第 7 步按缺译交付 partial。

```bash
python3 $S/assemble_translation.py --work $W --out $O   # 7) 组装纯译文+双语对照
python3 $S/align_engine.py audit --work $W --out $O     # 8) 对齐全覆盖核对
cat $W/align_audit.json   # 重点：missing / suspect / invariants
```

**第 9 步（Agent 复核与修订，禁止跳过）**：
1. **缺译清零**：补齐 missing 句段译文（追加 translations.jsonl），重跑 7、8。
2. **疑似项裁决**：长度异常句段逐条对照原文——漏译从句则补译；原文本身极短/极长（如枚举、标题式句子）在 findings.json 标“已驳回”并写理由。
3. **结构不一致修复**：图表编号集合、脚注标记不一致时，回到对应题注/脚注句段修复。

```bash
# 10) 报告 + 契约组装 + 闸门 + 预览
python3 $S/report_builder.py --work $W --out $O --focus alignment --skill "bilingual-alignment-guard v1.0.2"
python3 $S/assemble_result.py --work $W --out $O --skill "bilingual-alignment-guard v1.0.2" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理

| 情况 | 处置 |
|-|-|
| 无稿件候选 / 空文件 | 保留骨架 status=failed，exceptions 记录 |
| PDF 无文本层 | exceptions 记录；图表题注可能丢失，uncertainty 标注 |
| 平铺文本无章节标题 | 按虚拟单章处理，对照关系仍按段落建立 |
| 原文本身为双语稿 | 按 task.md 指定语向抽取原文侧；uncertainty 记录 |
| 表格为图片 | 图注可译，表内文字不可读，uncertainty 标注“未纳入” |
| 超长稿件 | 分批翻译；预算过半优先正文，附录允许缺译 partial |
| 脚本异常 | 读 stderr 修复重跑（幂等）；否则保留已有产物 partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `bilingual.md` | 双语对照稿：逐段 〔PID·原文〕/〔PID·译文〕，可直接逐段修改 |
| `translation_full.md` | 纯译文（结构原位） |
| `alignment.json` | 逐句段对齐状态（aligned/missing/suspect_length/kept_original） |
| `align_audit.json` | 对齐汇总：结构不变量与各类计数 |
| `report.md` / `findings.json` / `edit_plan.json` | 质量报告与修订清单 |
| `result.json` | 契约结果：case_id、status、evidence_map、change_log、uncertainty |

## 关键方法（详见 references/）

- `references/alignment_rules.md`：句段六分类、结构不变量定义、长度比例判据、合译/分译约定。
- `references/failure_modes.md`：误报来源与复核要点。
- `references/worked_example.md`：完整标注示例（合成，非正式案例）。

## 限制

- 长度比例为启发式（中英字符/词比 0.55–4.5），只能发现“疑似”漏译增译，定性靠复核。
- 图片内文字、扫描版 PDF 无文本层内容不纳入对齐，uncertainty 如实标注。
- 对照稿以段落为最小阅读单元、句段为最小定位单元；词级对齐不在本版本范围。
