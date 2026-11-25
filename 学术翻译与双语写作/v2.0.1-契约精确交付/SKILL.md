---
name: contract-exact-delivery
description: 学术翻译技能（v2 迭代·主攻“结果可核验性与完整性”：契约精确交付）。在句段级翻译管线（父辈 v1.0.1 数字台账+双向比对）上增加契约填充闸门：contract_fill.py 读取 case.json 的 output_contract 逐字段说明，把每个契约字段与实际产物做关键词语义匹配，写入含文件名/sha256/字节数/内容摘要/内容预览的结构化条目；内置数据字段（uncertainty/change_log 等）保留语义数据不覆盖；匹配不到的字段如实置 null 并记 uncertainty（可用 contract_override.json 人工指定映射），杜绝“字段存在但内容空泛”的契约注水。当用户要求按给定 output_contract 交付结构化翻译结果时使用；输入 /input 下稿件与 case.json，输出 /app/output 下 translation_full.md、bilingual.md、number_ledger.json、number_audit.json、report.md、逐字段填充的 result.json。
---

# 契约精确交付 · 学术翻译 Skill（v2.0.1，父辈 v1.0.1）

## 用途与适用条件

整篇学术稿件句段级翻译 + 数字忠实性机检（父辈机制）。**本版核心增量：result.json 从“别名兜底”升级为“逐字段语义化填充”**——每个 output_contract 字段都有真实、可定位、带哈希与预览的内容，匹配失败如实标注。

适用：一切带 output_contract 的翻译评测任务。不适用：纯数据无正文文件（如实降级）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、稿件；工作目录 `/app/work`；交付 `/app/output`。
- 预算：64 次模型请求 / 900 秒。译文追加写入 translations.jsonl，随时可组装部分结果。
- 本目录即技能根：`scripts/`、`references/`、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线

1. **契约不注水**：填充内容必须来自真实产物文件（带 sha256 与预览）；匹配不到的字段置 null 并记 uncertainty，禁止用空泛占位文本冒充。
2. **数字零臆造**：译文每个数字必须能在源句段找到等值对应。
3. **不静默跳过句段**：未译句段以【缺译】标记并计 uncertainty。

## 标准工作流（严格按序执行）

```bash
SKILL_DIR=/skills/weekly-skill   # 平台安装路径；本地调试用本目录
W=/app/work; O=/app/output; mkdir -p $W $O
S=$SKILL_DIR/scripts

python3 $S/init_result.py                       # 1) 兜底骨架
python3 $S/inspect_case.py --work $W            # 2) 案例侦察（含 output_contract 清单）
cat $W/inspection.json    # 重点：output_contract 各字段名与 spec——交付必须逐字段对应
python3 $S/parse_manuscript.py --work $W        # 3) 结构解析
python3 $S/segment_builder.py --work $W         # 4) 句段切分
python3 $S/number_engine.py ledger --work $W    # 5) 数字台账
```

**第 6 步（Agent 翻译）**：打开 `work/source_for_translation.md` 分批翻译（每批 20–40 句段），追加写 `work/translations.jsonl`；数字对照台账，〔保留:…〕逐字符保留。预算兜底：请求用满 40 次仍未译完，进第 7 步按缺译交付 partial。

```bash
python3 $S/assemble_translation.py --work $W --out $O   # 7) 组装纯译文+双语对照
python3 $S/number_engine.py audit --work $W             # 8) 数字双向比对
```

**第 9 步（Agent 复核修订，禁止跳过）**：处置 number_audit 的 issues，重跑 7、8 清零。

```bash
# 10) 报告 + 契约组装
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "contract-exact-delivery v2.0.1"
python3 $S/assemble_result.py --work $W --out $O --skill "contract-exact-delivery v2.0.1" --status success

# 11) 契约精确填充（本版核心步骤，禁止跳过）
python3 $S/contract_fill.py --work $W --out $O
cat $O/result.json | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)['contract_fill'],ensure_ascii=False,indent=1))"
```

**第 12 步（Agent 契约复核）**：
1. 检查 `contract_fill.unmapped`：对每个未映射字段，判断应交付什么——若现有产物可对应，写 `work/contract_override.json`（如 `{"修订记录": "edit_plan.json"}`）并重跑第 11 步；若任务确无此交付物，保留 null（uncertainty 已有记录）。
2. 抽查已映射字段的 `content_preview` 是否与字段语义相符；不符者用 override 纠正。
3. 重跑闸门：

```bash
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理

| 情况 | 处置 |
|-|-|
| 无稿件候选 / 空文件 | 保留骨架 status=failed，exceptions 记录 |
| case.json 无 output_contract | contract_fill 直接通过（打印无需填充），result.json 保持标准字段 |
| 契约字段语义模糊无法匹配 | 置 null + uncertainty 记录；Agent 在第 12 步 override 或确认 |
| override 指定文件不存在 | 回退自动匹配并记 uncertainty（不静默采用坏映射） |
| PDF 无文本层 / 稿件无数字 | exceptions/零发现如实记录；status≤partial 或 success（无数字不构成失败） |
| 超长稿件 / 脚本异常 | 分批 partial 兜底；脚本读 stderr 修复重跑（幂等） |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `translation_full.md` / `bilingual.md` | 纯译文 / 双语对照 |
| `number_ledger.json` / `number_audit.json` | 数字台账与双向比对表 |
| `report.md` / `findings.json` / `edit_plan.json` | 质量报告与修订清单 |
| `result.json` | 契约结果：标准字段 + 逐字段语义条目（file/sha256/bytes/summary/content_preview/verified）+ contract_fill 映射报告 |

## 关键方法（详见 references/）

- `references/contract_mapping.md`：产物注册表、关键词打分、override 机制、内置字段保护。
- `references/number_rules.md`：数字归一与改动分级（父辈机制）。
- `references/failure_modes.md`：误报来源与复核要点。
- `references/worked_example.md`：完整标注示例（合成，非正式案例）。

## 限制

- 关键词匹配是启发式，最终映射正确性由第 12 步 Agent 复核保证。
- 契约字段要求内联长文（而非文件引用）时，content_preview 只含前 300 字符，
  完整内容以 file 字段指向的产物为准（在 summary 注明）。
