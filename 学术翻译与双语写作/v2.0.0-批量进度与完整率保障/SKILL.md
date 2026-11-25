---
name: translation-completion-guard
description: 学术翻译技能（v2 迭代·主攻“任务完成度”：批量进度与整篇完整率保障）。在句段级翻译管线上增加批量工程：脚本把待译句段预切为批文件（每批≤15 句段、自带填写模板与保留约束），Agent 逐批翻译追加、batch_planner 实时报告进度/下一批/预算告警（剩余请求不足时自动建议并批与优先级策略），保证 64 次请求/900 秒内整篇 100% 覆盖交付，杜绝缺译与超时空手。继承 v1.0.1 父辈管线：数字台账+双向比对机检。当用户要求整篇翻译论文、双语对照稿，尤其长文、预算受限时使用；输入 /input 下稿件（md/txt/tex/docx/pdf）与 case.json，输出 /app/output 下 translation_full.md、bilingual.md、number_ledger.json、number_audit.json、report.md、result.json。
---

# 批量进度与完整率保障 · 学术翻译 Skill（v2.0.0，父辈 v1.0.1）

## 用途与适用条件

整篇学术稿件句段级翻译。**本版核心增量：把“译完整”从依赖自觉变为工程保证**——预切批文件、进度追踪、预算告警；父辈的数字台账与忠实性比对全部保留。

适用：长文/预算受限的整篇翻译（英译中、中译英）。不适用：纯数据无正文文件（如实降级）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、稿件；工作目录 `/app/work`；交付 `/app/output`。
- 预算：64 次模型请求 / 900 秒。**每批一次写盘；status 随时可查剩余与建议**。
- 本目录即技能根：`scripts/`、`references/`、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线

1. **数字零臆造**：译文每个数字必须能在源句段找到等值对应。
2. **不静默跳过句段**：批次未译句段以【缺译】标记并计 uncertainty；预算告警时必须按优先级策略处置，不得停手。
3. **等值换算才允许**：万/亿↔million/billion 只允许数学等值，禁止四舍五入与顺手改整。

## 标准工作流（严格按序执行）

```bash
SKILL_DIR=/skills/weekly-skill   # 平台安装路径；本地调试用本目录
W=/app/work; O=/app/output; mkdir -p $W $O
S=$SKILL_DIR/scripts

python3 $S/init_result.py                       # 1) 兜底骨架（防超时空手）
python3 $S/inspect_case.py --work $W            # 2) 案例侦察（方向/形态/任务类型）
python3 $S/parse_manuscript.py --work $W        # 3) 结构解析（稳定 ID）
python3 $S/segment_builder.py --work $W         # 4) 句段切分 + 受保护片段
python3 $S/number_engine.py ledger --work $W    # 5) 数字台账（译前约束）
python3 $S/batch_planner.py plan --work $W --batch-size 15   # 6) 批文件 + 进度表
```

**第 7 步（Agent 翻译主循环，严格按批执行）**：

```bash
cat $W/progress.json          # 看批次表
# 循环：读一个批文件 → 翻译该批 → 追加 work/translations.jsonl → status 查下一批
cat $W/batches/batch_01.md
# （翻译，每行一个 JSON：{"seg_id":"P001-s1","translation":"…"}，追加写入 $W/translations.jsonl）
python3 $S/batch_planner.py status --work $W --used-requests <你已用的模型请求数>
```

- 一次响应可翻译并写入**多批**（status 提示预算紧张时必须并批：一次写 2-3 批）。
- 批文件自带约束提示：〔保留:…〕逐字符保留；数字对照 number_ledger。
- **预算告警**（剩余请求 < 剩余批次+8）时的优先级：正文 body > heading > caption > footnote；
  低优先级句段允许【缺译】partial，但正文必须 100%。
- 翻译全部完成后 status 显示“进入组装与机检阶段”再往下走。

```bash
python3 $S/assemble_translation.py --work $W --out $O   # 8) 组装纯译文+双语对照
python3 $S/number_engine.py audit --work $W             # 9) 数字双向比对
cat $W/number_audit.json
```

**第 10 步（Agent 复核与修订，禁止跳过）**：逐条处置 number_audit 的 issues（误报驳回写理由、真错追加修订译文），重跑 8、9 确认清零；同步核查 stats.json 的 coverage=1.0（缺译句段补译或确认 partial）。

```bash
# 11) 报告 + 契约组装 + 闸门 + 预览
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "translation-completion-guard v2.0.0"
python3 $S/assemble_result.py --work $W --out $O --skill "translation-completion-guard v2.0.0" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理

| 情况 | 处置 |
|-|-|
| 无稿件候选 / 空文件 | 保留骨架 status=failed，exceptions 记录 |
| PDF 无文本层 | exceptions 记录；status≤partial |
| 预算告警触发 | 按第 7 步优先级并批；仍不足则正文优先、其余缺译 partial（uncertainty 写明） |
| 批文件与 segments 不一致（重跑 plan 后） | progress.json 以最新 plan 为准，已译 JSONL 不受影响 |
| 稿件无数字 | ledger/audit 零发现，不构成失败 |
| 超长稿件（>600 句段） | --batch-size 20，预算告警阈值自动生效 |
| 脚本异常 | 读 stderr 修复重跑（幂等）；否则保留已有产物 partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `translation_full.md` / `bilingual.md` | 纯译文 / 双语对照（结构原位，覆盖率见 stats） |
| `progress.json` / `batches/` | 进度表与批文件（过程资产，可断点续译） |
| `number_ledger.json` / `number_audit.json` | 数字台账与双向比对表 |
| `report.md` / `findings.json` / `edit_plan.json` | 质量报告与修订清单 |
| `result.json` | 契约结果：case_id、status、evidence_map、change_log、uncertainty、stats |

## 关键方法（详见 references/）

- `references/completion_engineering.md`：批量工程、进度语义、预算告警阈值与优先级策略。
- `references/number_rules.md`：数字归一与改动分级（父辈机制）。
- `references/failure_modes.md`：误报来源与复核要点。
- `references/worked_example.md`：完整标注示例（合成，非正式案例）。

## 限制

- 预算告警基于 Agent 自报的已用请求数，Agent 须如实计数。
- 批量切分不改变翻译质量本身，质量由数字机检与 Agent 复核保证。
- 中文大写/罗马数字等特殊记数不纳入机检（uncertainty 标注）。
