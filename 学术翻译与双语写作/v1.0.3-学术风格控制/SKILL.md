---
name: academic-style-control
description: 学术翻译技能（主攻“学术风格·语域稳”）。整篇翻译完成后对译文做语域与句式机检：直译痕迹（中文目标的动词名词化“进行了研究”、被动滥用、超长前置定语、英式连接“对于…来说”；英文目标的 It is well known that / with the development of / more and more）与语域越界（宣传口吻“革命性/突破性/完美”、口语化、第一人称单数、感叹号、超长句），逐句段定位并给出具体改写指令，Agent 据此修订译文后复检，把学术表述从直译腔拉回目标学科学术语域，同时守住克制语气、不改成宣传口吻。适用于论文翻译稿的润色与风格统一、双语写作的语气控制；不适用于尚无译文的纯原文（需先完成翻译管线）。输入 /input 下稿件与 case.json，输出 /app/output 下 translation_full.md、bilingual.md、style_report.json（指标+逐句段问题）、report.md、result.json。
---

# 学术风格控制 · 学术翻译 Skill

## 用途与适用条件

对完整学术稿件做句段级翻译，并对译文做**语域与句式双重机检**，主攻题面“学术风格”：避免逐字直译造成的冗长与生硬，同时不把学术表述改成宣传口吻或口语化表达。机制：脚本出**风格指标与逐句段问题清单**（秒级），Agent 负责翻译与文学性修订——脚本不自动改写。

适用：翻译稿润色、双语写作风格统一。不适用：尚无译文的场景（先跑翻译管线）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、稿件；工作目录 `/app/work`；交付 `/app/output`。
- 预算：64 次模型请求 / 900 秒。译文追加写入 translations.jsonl，随时可组装。
- 本目录即技能根：`scripts/`、`references/`、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线

1. **风格修订不改事实**：修订只动句式与措辞，数字、单位、术语、引用、否定与限定条件逐字保留；拿不准的表述改写列入 manual_confirmations。
2. **不把克制译成宣传**：原文无确定性/夸大表述时，修订不得引入“革命性/突破性/证明/必然”类升格词（机检同样拦译文侧）。
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
```

**第 5 步（Agent 翻译）**。打开 `work/source_for_translation.md` 分批翻译（每批 20–40 句段），追加写 `work/translations.jsonl`。翻译期就遵守 references/style_rules.md 的语域规范（主动优先、动词谓语、定语从短、克制语气），减少返工。预算兜底：请求用满 40 次仍未译完，进第 6 步按缺译交付 partial。

```bash
python3 $S/assemble_translation.py --work $W --out $O   # 6) 组装纯译文+双语对照
python3 $S/style_engine.py audit --work $W              # 7) 风格机检（指标+逐句段问题）
cat $W/style_report.json    # 重点：metrics（的密度/被字密度）与 segments 各 issues
```

**第 8 步（Agent 风格修订，禁止跳过）**：
1. **逐条处理 style_report**：对每条 issue 按 instruction 改写译文（追加 translations.jsonl 同 seg_id 覆盖）；同类问题在同篇其他句段主动排查。
2. **删误报**：被动确为习惯表达（“被称为”“被认为是”）、宣传词出现在被引文献标题或反讽语境等，在 findings.json 标“已驳回”并写理由。
3. **复检**：重跑第 6、7 步，确认高严重度清零；metrics 改善幅度写入 report。

```bash
# 9) 报告 + 契约组装 + 闸门 + 预览
python3 $S/report_builder.py --work $W --out $O --focus style --skill "academic-style-control v1.0.3"
python3 $S/assemble_result.py --work $W --out $O --skill "academic-style-control v1.0.3" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理

| 情况 | 处置 |
|-|-|
| 无稿件候选 / 空文件 | 保留骨架 status=failed，exceptions 记录 |
| PDF 无文本层 | exceptions 记录；status≤partial |
| 目标语不是中/英 | 风格规则库不含该语言：uncertainty 标注，仅交付翻译管线产物 |
| 文体非学术（新闻稿、说明书） | task.md 明示则按其文体，style 规则降级为提示并记录 |
| 译文整体风格良好（零发现） | report 如实报告零发现与 metrics，不虚构问题 |
| 超长稿件 | 分批翻译；风格机检按全量译文运行（秒级，无预算压力） |
| 脚本异常 | 读 stderr 修复重跑（幂等）；否则保留已有产物 partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `translation_full.md` / `bilingual.md` | 风格修订后的纯译文 / 双语对照 |
| `style_report.json` | 风格指标（的密度、被字密度、长句分布）+ 逐句段问题与改写指令 |
| `report.md` / `findings.json` / `edit_plan.json` | 质量报告与修订清单 |
| `result.json` | 契约结果：case_id、status、evidence_map、change_log（自动记录译文修订 diff）、uncertainty |

## 关键方法（详见 references/）

- `references/style_rules.md`：直译痕迹四类、语域越界三类、句式长度判据、改写范式表。
- `references/failure_modes.md`：误报来源与复核要点。
- `references/worked_example.md`：完整标注示例（合成，非正式案例）。

## 限制

- 规则库覆盖高频直译腔与语域问题，不能穷尽所有风格问题；Agent 文学性判断是最终保证。
- 机检提供指标与候选，不自动改写——避免机器润色引入事实漂移。
- 学科特定文体惯例（如数学论文的 "we"、医学的被动语态倾向）由 Agent 按 task.md 与学科调整。
