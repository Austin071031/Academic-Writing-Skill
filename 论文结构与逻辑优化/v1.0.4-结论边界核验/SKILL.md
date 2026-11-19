---
name: conclusion-boundary-check
description: 论文结构诊断技能（主攻"结论边界与表述尺度"）。对完整稿件做六维结构普查（研究问题/章节结构/论证链/段落关系/重复内容/结论边界），并深度核验结论是否超出数据与实验条件：结论/摘要数字逐条溯源（无源数字、四舍五入与笔误、格式不一致）、摘要-结论同语境数字一致性、因果表述三档裁决（把相关当因果）、绝对化与推广超界表述、局限性说明缺失/位置/充分性。所有问题定位到章节/段落/句子并附原文锚点与可执行编辑动作（非改写稿）。当用户要求检查论文结论是否夸大、数字是否有出处、因果与相关是否混淆、局限性说明是否充分时使用；输入为 /input 下稿件（md/txt/tex/docx/pdf）与 case.json，输出 /app/output 下 diagnosis_report.md、edit_plan.json、findings.json、boundary_audit.json、result.json。
---

# 结论边界与表述尺度核验 · 结构诊断 Skill

## 用途与适用条件

对一篇**完整稿件**执行结构诊断，交付作者可直接执行的编辑计划。主攻维度：**结论边界与表述尺度**——结论是否超出数据与实验条件、是否遗漏限制说明、是否把相关当因果、结论与摘要数字是否一致、是否存在无源数字；同时用六维普查保证覆盖面（评分与复核都要求不缺维度）。

适用：期刊/会议论文、学位论文章节、实验报告（中英双语）。不适用：无正文段落的纯数据文件（按"材料缺口"如实降级）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、稿件材料；工作目录 `/app/work`；交付目录 `/app/output`。
- 预算：64 次模型请求 / 900 秒。**脚本承担全部机械劳动（秒级），模型只做判断与修订**。
- 本目录即技能根：`scripts/`（管线）、`references/`（规则与判据）、`docs/USAGE.md`、`examples/minimal_example.md`。

## 标准工作流（严格按序执行）

```bash
SKILL_DIR=/skills/weekly-skill   # 平台安装路径；本地调试用本目录
W=/app/work; O=/app/output; mkdir -p $W $O
S=$SKILL_DIR/scripts

# 1) 兜底骨架（防超时空手；幂等）
python3 $S/init_result.py

# 2) 案例侦察：case_id、output_contract、稿件候选、材料缺口
python3 $S/inspect_case.py --work $W
cat $W/inspection.json        # 只读摘要部分即可

# 3) 结构解析：章节/段落/句子稳定 ID（SEC1/P001/P001-s2）
python3 $S/parse_manuscript.py --work $W
#    多稿件时用 --file 指定；PDF 依赖 pdftotext，失败如实降级

# 4) 六维轻量普查（保证完整性，输出 findings_scan.json）
python3 $S/six_scan.py --work $W

# 5) 主攻引擎：数字溯源表、因果三档、范围比对、限制审计（boundary_audit.json）
python3 $S/boundary_audit.py --work $W
cat $W/boundary_audit.json    # 重点阅读 number_provenance 各条 verdict 与 summary

# 6) 生成可交付草稿：diagnosis_report.md + edit_plan.json + findings.json
python3 $S/report_builder.py --work $W --out $O \
    --focus conclusion_boundary --skill "conclusion-boundary-check v1.0.4"
```

## 第 7 步：Agent 判断（本技能的核心增值，禁止跳过）

脚本产出的是**候选**问题。你必须打开 `$O/diagnosis_report.md` 与 `$W/boundary_audit.json` 做三轮判断：

1. **删误报**：对照 `$W/structure.json` 中原文（按 finding 的 para_id/sentence_id 索引），删除确不成立的条目；尤其注意：四舍五入差异（65.2%→65%）被升级为"笔误"的候选、编号/年份被误当数据的候选、单位换算差异（0.873 vs 87.3%）被误判"无源"的候选（复核要点见 references/failure_modes.md）。
2. **补漏报**：通读结构模型，补充脚本未捕获的**真实**越界（每条必须有：维度、类型、位置、原文锚点 quote、依据、编辑动作 op+instruction、severity、confidence、status=待作者复核），追加进 `$O/findings.json` 并在报告中同步。**禁止虚构缺陷**：找不到原文锚点的问题一律不写。
3. **定优先级**：按"是否误导读者对结论强度的判断"重排 severity（无源数字、相关当因果通常最高）；在报告开头补 3-5 句总体诊断（主要问题在数字溯源还是表述尺度、为什么）。

编辑动作只允许这 9 类：`move / merge / split / narrow / qualify / add / add_transition / add_limitation / reorder`。**不产出另起炉灶的改写稿**。

## 第 8 步：交付与闸门

```bash
# 状态诚实：全部完成=success；材料缺口/部分维度无法判断=partial（在 uncertainty 写明）
python3 $S/assemble_result.py --work $W --out $O \
    --skill "conclusion-boundary-check v1.0.4" --status success
python3 $S/validate_output.py --out $O --work $W   # 必须 PASS
```

`/app/output/result.json` 自动回填 case.json 声明的全部 output_contract 字段 + case_id，含 evidence_map（逐条指回原文位置）、change_log、uncertainty。

## 异常处理（识别并如实记录，不得静默）

| 情况 | 处置 |
|-|-|
| 无稿件候选 / 空文件 | init 骨架保留 → status=failed，exceptions 记录原因 |
| PDF 无 pdftotext 或抽取为空 | exceptions 记录；status≤partial |
| 未识别到章节标题（平铺文本） | 按虚拟单章处理；溯源/范围类置信度≤0.5，uncertainty 标注 |
| 多个稿件候选 | 取 inspection 排序第一并在 uncertainty 列出其余候选 |
| 稿件疑似截断 | parse 已检测；结论边界类条目全部标"需人工确认" |
| 无方法/实验章 | 因果三档降级为 unverifiable/overreach（无设计词可检）；范围比对注明"无法核验" |
| 任一脚本异常 | 读 stderr；能修复则修复后重跑（脚本幂等）；不能则保留已有产物，status=partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `diagnosis_report.md` | 六维诊断报告：每条问题含位置/原文锚点/依据/编辑动作/严重度/置信度/复核状态 |
| `edit_plan.json` | 机读编辑动作清单（与 findings 同 id，供逐条勾选采纳/驳回） |
| `findings.json` | 全部问题统一 schema（脚本候选 + Agent 增删后） |
| `boundary_audit.json` | 数字溯源表（逐条 verdict）、因果三档表、范围比对表、限制审计（可复核中间产物） |
| `result.json` | 契约结果：case_id、status、outputs、evidence_map、change_log、uncertainty、stats |

## 关键方法（详见 references/）

- `references/boundary_rules.md`：数字溯源三层匹配与容差、因果三档、绝对化、推广范围比对、限制充分性、摘要-结论一致性判据。
- `references/boundary_taxonomy.md`：结论边界类问题分类（无源数字/数字不一致/因果超界/绝对化/推广超界/缺限制说明/摘要结论不符）。
- `references/worked_example.md`：完整标注示例（合成稿件，非正式案例）。
- `references/failure_modes.md`：误报来源与人工复核要点（四舍五入、编号年份、单位换算）。

## 限制

- 数字溯源基于词面与数值比对，无法识别"数字来自被引文献"等语义出处——这类条目由第 7 步人工确认。
- 因果三档依赖设计词/相关性词命中，实验设计描述非常规措辞时判 unverifiable（置信度低，人工复核）。
- 不生成全文改写稿；编辑动作由作者执行（题面"改得动"要求）。
