---
name: task-adaptive-translation
description: 学术翻译与双语写作技能（v2 迭代·主攻“跨案例任务完成度”：任务类型自适应）。inspect_case 从 task.md 与材料角色识别四类任务：整篇翻译（默认）、译文校对审校/后编辑（材料含现有译文）、带修订标记的修改、基于材料的双语写作；校对/修订模式用 align_existing_translation.py 把已有译文句子按长度比例映射回源文句段坐标直接生成 translations.jsonl（异常映射标 needs_review），Agent 转入审校+修订角色，机检/双语对照/标注稿交付完全复用；双语写作模式以句段骨架为约束组织新写内容。继承 v1.0.1 父辈数字台账+双向比对。当任务可能是翻译、译文校对、修订或双语写作中任一种时使用；输入 /input 下材料与 case.json，输出 /app/output 下 translation_full.md、bilingual.md、audit_annotated.md（校对/修订模式）、number_audit.json、report.md、result.json。
---

# 任务类型自适应 · 学术翻译 Skill（v2.0.2，父辈 v1.0.1）

## 用途与适用条件

题面固定案例的任务类型不限于“整篇翻译”：可能是**译文校对审校**（材料已含译文）、
**带修订标记的修改**、或**基于材料的双语写作**。v1 管线一律按整篇翻译处理会错配。
**本版核心增量：先识别任务类型，再分支执行**；校对模式把已有译文映射回句段坐标，
机检与交付管线完全复用。

适用：四类任务混合的翻译评测。不适用：无正文材料（如实降级）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、材料；工作目录 `/app/work`；交付 `/app/output`。
- 预算：64 次模型请求 / 900 秒。
- 本目录即技能根：`scripts/`、`references/`、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线

1. **任务类型如实判定**：以 task.md 为准；识别置信度低时在 uncertainty 写明所选分支与理由，不得暗自按最省事分支执行。
2. **数字零臆造 / 不静默跳过句段**（同父辈）。
3. **校对模式不改写事实**：审校修订只纠正错误与风格，已有译文正确部分保留原样，全部修订进 change_log。

## 标准工作流（分支执行）

```bash
SKILL_DIR=/skills/weekly-skill   # 平台安装路径；本地调试用本目录
W=/app/work; O=/app/output; mkdir -p $W $O
S=$SKILL_DIR/scripts

python3 $S/init_result.py
python3 $S/inspect_case.py --work $W
cat $W/inspection.json
# 重点：translation_task.task_type ∈
#   full_translation / proofread_translation / revise_tracked / bilingual_writing
# 以及 material_roles（source_manuscript / existing_translation）
```

### 分支 A：full_translation（默认，整篇翻译）

```bash
python3 $S/parse_manuscript.py --work $W
python3 $S/segment_builder.py --work $W
python3 $S/number_engine.py ledger --work $W
# Agent 分批翻译 source_for_translation.md → work/translations.jsonl
# （预算兜底：请求 40 次后未译完则跳组装交付 partial）
```

### 分支 B：proofread_translation / revise_tracked（材料含现有译文）

```bash
# 1) 解析源文（--file 指定原文，不是译文！）
python3 $S/parse_manuscript.py --work $W --file /input/<原文文件>
python3 $S/segment_builder.py --work $W
python3 $S/number_engine.py ledger --work $W
# 2) 已有译文对齐回句段坐标（本版核心）
python3 $S/align_existing_translation.py --work $W \
    --translation-file /input/<译文文件>
cat $W/existing_translation_alignment.json   # 重点：coverage 与 needs_review
```

**Agent 复核对齐（禁止跳过）**：逐条处理 needs_review 与 coverage<90% 的告警——
对照源文修正 translations.jsonl 中的错位映射（改 seg_id 或拆分合并），
无法对应的句段保持缺译并说明。

### 分支 C：bilingual_writing（基于材料双语写作）

以 segments.json 句段骨架为结构约束，由 Agent 依据材料事实**撰写**双语内容
写入 translations.jsonl（同 seg_id 对应原文依据句段）；数字/引用必须能在材料中溯源，
无源内容在 manual_confirmations 标注。随后进入公共机检。

### 公共阶段（所有分支）

```bash
python3 $S/assemble_translation.py --work $W --out $O   # 纯译文 + 双语对照
python3 $S/number_engine.py audit --work $W             # 数字双向比对
# 分支 B/C 追加：对齐覆盖与映射复核结论写入 work/manual_confirmations.json
```

**Agent 复核修订（禁止跳过）**：分支 B 的修订通过向 translations.jsonl 追加
同 seg_id 新译文完成（change_log 自动记录 diff，即为修订痕迹）；交付形态为
tracked 时，report 与 ⚠ 标注文件即为修订标记产物。重跑组装与机检确认清零。

```bash
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "task-adaptive-translation v2.0.2"
python3 $S/assemble_result.py --work $W --out $O --skill "task-adaptive-translation v2.0.2" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理

| 情况 | 处置 |
|-|-|
| 任务类型置信度低 | uncertainty 写明所选分支与理由；按最保守分支（full_translation）执行 |
| 校对模式未识别到译文文件 | inspection issues 已提示；Agent 用 --translation-file 显式指定 |
| 对齐覆盖率 <90% | 复核映射；译文本身不完整则缺译句段按 partial 处理并注明 |
| 材料只有译文没有原文 | 无法建立句段坐标：status≤partial，仅交付通用校对意见并说明限制 |
| 双语写作无足够材料事实 | 缺口部分标注 manual_confirmations，不虚构 |
| 脚本异常 | 读 stderr 修复重跑（幂等）；否则保留已有产物 partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `translation_full.md` / `bilingual.md` | 纯译文（或修订后译文）/ 双语对照 |
| `existing_translation_alignment.json` | 分支 B：已有译文-句段映射与 needs_review 清单 |
| `audit_annotated.md` | 分支 B/tracked：⚠ 审校标注稿 |
| `number_ledger.json` / `number_audit.json` | 数字台账与比对（所有分支） |
| `result.json` | 契约结果：case_id、status、evidence_map、change_log（修订痕迹）、uncertainty |

## 关键方法（详见 references/）

- `references/task_adaptation.md`：四类任务识别特征、材料角色判定、对齐算法与置信度。
- `references/number_rules.md`：数字归一与改动分级（父辈机制）。
- `references/failure_modes.md`：误报来源与复核要点。

## 限制

- 已有译文对齐为长度比例启发式，错位映射依赖 Agent 复核（needs_review 已全部标出）。
- 任务类型识别基于 task.md 关键词；表述非常规时按保守分支执行并记录。
