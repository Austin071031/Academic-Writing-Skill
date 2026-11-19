---
name: argument-chain-audit
description: 论文结构诊断技能（主攻"论证链与论据对应"）。对完整稿件做六维结构普查（研究问题/章节结构/论证链/段落关系/重复内容/结论边界），并深度核验论证链：逐条抽取论断（比较/因果/概括/绝对）并映射其支撑论据锚点（引用/图表/带单位数字/交叉引用），找出论证链断裂、跨段逻辑跳跃、疑似循环论证、论据强度不足、比较无对象。所有问题定位到章节/段落/句子并附原文锚点与可执行编辑动作（非改写稿）。当用户要求检查论文结构、论证是否严密、论断有无证据支撑、论据与结论是否匹配时使用；输入为 /input 下稿件（md/txt/tex/docx/pdf）与 case.json，输出 /app/output 下 diagnosis_report.md、edit_plan.json、findings.json、chain_audit.json、result.json。
---

# 论证链与论据对应 · 结构诊断 Skill

## 用途与适用条件

对一篇**完整稿件**执行结构诊断，交付作者可直接执行的编辑计划。主攻维度：**论证链与论据对应**——逐条抽取论断并核验每条论断是否有锚点论据支撑、支撑强度是否匹配论断类型；同时用六维普查保证覆盖面（评分与复核都要求不缺维度）。

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

# 5) 主攻引擎：论断抽取、论据锚点、论断—论据映射三档裁决（chain_audit.json）
python3 $S/chain_audit.py --work $W
cat $W/chain_audit.json       # 重点阅读 summary 与各条论断的支撑档
```

## 第 6 步：生成可交付草稿

```bash
python3 $S/report_builder.py --work $W --out $O \
    --focus argument_chain --skill "argument-chain-audit v1.0.2"
```

## 第 7 步：Agent 判断（本技能的核心增值，禁止跳过）

脚本产出的是**候选**问题。你必须打开 `$O/diagnosis_report.md` 与 `$W/chain_audit.json` 做三轮判断：

1. **删误报**：对照 `$W/structure.json` 中原文（按 finding 的 para_id/sentence_id 索引），删除确不成立的条目；尤其注意：文献综述中的转述论断（"已有工作表明…[n]"有锚点，不应在断裂清单）、段内数据以纯文本形式给出（无单位数字被漏检）导致的假"断裂"、近似复述实为正常重述（结论复述摘要）被误判"循环论证"的候选。
2. **补漏报**：通读结构模型，补充脚本未捕获的**真实**断裂（每条必须有：维度、类型、位置、原文锚点 quote、依据、编辑动作 op+instruction、severity、confidence、status=待作者复核），追加进 `$O/findings.json` 并在报告中同步。**禁止虚构缺陷**：找不到原文锚点的问题一律不写。
3. **定优先级**：按"是否阻断论证闭环"重排 severity（断裂/强度不足 > 循环 > 跳跃/比较无对象）；在报告开头补 3-5 句总体诊断（主要问题在哪个维度、为什么）。

编辑动作只允许这 9 类：`move / merge / split / narrow / qualify / add / add_transition / add_limitation / reorder`。**不产出另起炉灶的改写稿**。

## 第 8 步：交付与闸门

```bash
# 状态诚实：全部完成=success；材料缺口/部分维度无法判断=partial（在 uncertainty 写明）
python3 $S/assemble_result.py --work $W --out $O \
    --skill "argument-chain-audit v1.0.2" --status success
python3 $S/validate_output.py --out $O --work $W   # 必须 PASS
```

`/app/output/result.json` 自动回填 case.json 声明的全部 output_contract 字段 + case_id，含 evidence_map（逐条指回原文位置）、change_log、uncertainty。

## 异常处理（识别并如实记录，不得静默）

| 情况 | 处置 |
|-|-|
| 无稿件候选 / 空文件 | init 骨架保留 → status=failed，exceptions 记录原因 |
| PDF 无 pdftotext 或抽取为空 | exceptions 记录；status≤partial |
| 未识别到章节标题（平铺文本） | 按虚拟单章处理；结构类置信度≤0.5，uncertainty 标注 |
| 多个稿件候选 | 取 inspection 排序第一并在 uncertainty 列出其余候选 |
| 稿件疑似截断 | parse 已检测；结论边界类条目全部标"需人工确认" |
| 无参考文献/图表 | 不报错；论证链维度相应条目注明"证据锚点类型受限"，断裂类置信度下调 |
| 任一脚本异常 | 读 stderr；能修复则修复后重跑（脚本幂等）；不能则保留已有产物，status=partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `diagnosis_report.md` | 六维诊断报告：每条问题含位置/原文锚点/依据/编辑动作/严重度/置信度/复核状态 |
| `edit_plan.json` | 机读编辑动作清单（与 findings 同 id，供逐条勾选采纳/驳回） |
| `findings.json` | 全部问题统一 schema（脚本候选 + Agent 增删后） |
| `chain_audit.json` | 论断总数与分档统计、逐条论断—论据映射表（支撑档 strong/weak/none，可复核中间产物） |
| `result.json` | 契约结果：case_id、status、outputs、evidence_map、change_log、uncertainty、stats |

## 关键方法（详见 references/）

- `references/chain_rules.md`：论断抽取、锚点窗口、支撑分档、循环论证近似判定、强度匹配判据。
- `references/chain_taxonomy.md`：论证链问题分类（无锚点断裂/跨段跳跃/循环论证/强度不足/结论性语句无承接/比较级无对象）。
- `references/worked_example.md`：完整标注示例（合成稿件，非正式案例）。
- `references/failure_modes.md`：误报来源与人工复核要点。

## 限制

- 启发式规则面向中英文 IMRaD 类稿件；文学性文本、讲义、纯综述的锚点与论断判定置信度下降（报告中如实标注）。
- 支撑档基于锚点窗口的词面检测：同义改写、无单位数字、图表以"上图"等口语指代时会误判——这正是第 7 步 Agent 判断要补的部分。
- 循环论证为 3-gram 相似度近似判定，结论对摘要的正常复述可能命中，一律需人工确认。
- 不生成全文改写稿；编辑动作由作者执行（题面"改得动"要求）。
