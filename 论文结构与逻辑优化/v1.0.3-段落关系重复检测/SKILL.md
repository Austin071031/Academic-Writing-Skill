---
name: paragraph-redundancy-map
description: 论文结构诊断技能（主攻"段落关系与重复内容"）。对完整稿件做六维结构普查（研究问题/章节结构/论证链/段落关系/重复内容/结论边界），并深度核验段落级与句子级重复（同义重复、近似重复、跨章节重复）、段落间衔接缺失与话题跳变、回指悬空、多话题长段未拆分，给出合并、拆分与衔接建议。所有问题定位到章节/段落/句子并附原文锚点与可执行编辑动作（非改写稿）。当用户要求查重、压缩篇幅、合并重复段落、补过渡、拆分混杂段落时使用；输入为 /input 下稿件（md/txt/tex/docx/pdf）与 case.json，输出 /app/output 下 diagnosis_report.md、edit_plan.json、findings.json、redundancy_report.json、result.json。
---

# 段落关系与重复内容 · 结构诊断 Skill

## 用途与适用条件

对一篇**完整稿件**执行结构诊断，交付作者可直接执行的编辑计划。主攻维度：**段落关系与重复内容**（同义/近似重复、跨章节重复、段落缺过渡与逻辑跳跃、该拆分未拆分）；同时用六维普查保证覆盖面（评分与复核都要求不缺维度）。

适用：期刊/会议论文、学位论文章节、实验报告（中英双语），尤其适用于投稿前查重式自查与篇幅压缩。不适用：无正文段落的纯数据文件（按"材料缺口"如实降级）。

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

# 5) 主攻引擎：段落重复对/句子级跨章重复/衔接缺失/回指悬空/拆分候选（redundancy_report.json）
python3 $S/redundancy.py --work $W
cat $W/redundancy_report.json # 重点阅读 duplicate_pairs 与 statistics

# 6) 生成可交付草稿：diagnosis_report.md + edit_plan.json + findings.json
python3 $S/report_builder.py --work $W --out $O \
    --focus redundancy --skill "paragraph-redundancy-map v1.0.3"
```

## 第 7 步：Agent 判断（本技能的核心增值，禁止跳过）

脚本产出的是**候选**问题。你必须打开 `$O/diagnosis_report.md` 与 `$W/redundancy_report.json` 做三轮判断：

1. **删误报**：对照 `$W/structure.json` 中原文（按 finding 的 para_id/sentence_id 索引），删除确不成立的条目；尤其注意：摘要与引言/结论的点题性呼应（结构性呼应条目 confidence≤0.6，须逐条裁决，不可全删也不可全留）、方法章对实验设置的标准表述重合（同一套参数写两遍可能是必要复现）、文献综述中同义复述他人观点的正常学术行为。
2. **补漏报**：通读结构模型，补充脚本未捕获的**真实**断裂（每条必须有：维度、类型、位置、原文锚点 quote、依据、编辑动作 op+instruction、severity、confidence、status=待作者复核），追加进 `$O/findings.json` 并在报告中同步。**禁止虚构缺陷**：找不到原文锚点的问题一律不写。
3. **定优先级**：按"重复是否造成读者读到两遍同一论证"重排 severity；在报告开头补 3-5 句总体诊断（重复集中在哪些章节、冗余规模约多少字符、衔接断裂在哪里）。

编辑动作只允许这 9 类：`move / merge / split / narrow / qualify / add / add_transition / add_limitation / reorder`。**不产出另起炉灶的改写稿**。

## 第 8 步：交付与闸门

```bash
# 状态诚实：全部完成=success；材料缺口/部分维度无法判断=partial（在 uncertainty 写明）
python3 $S/assemble_result.py --work $W --out $O \
    --skill "paragraph-redundancy-map v1.0.3" --status success
python3 $S/validate_output.py --out $O --work $W   # 必须 PASS
```

`/app/output/result.json` 自动回填 case.json 声明的全部 output_contract 字段 + case_id，含 evidence_map（逐条指回原文位置）、change_log、uncertainty。

## 异常处理（识别并如实记录，不得静默）

| 情况 | 处置 |
|-|-|
| 无稿件候选 / 空文件 | init 骨架保留 → status=failed，exceptions 记录原因 |
| PDF 无 pdftotext 或抽取为空 | exceptions 记录；status≤partial |
| 未识别到章节标题（平铺文本） | 全部段落按虚拟单章处理；跨章判据失效，衔接/拆分类置信度≤0.5，uncertainty 标注 |
| 多个稿件候选 | 取 inspection 排序第一并在 uncertainty 列出其余候选 |
| 稿件疑似截断 | parse 已检测；结论边界类条目全部标"需人工确认" |
| 无参考文献/图表 | 不报错；交叉引用建议的锚点类型受限（建议用"第X节"文本锚点） |
| 达标段落超两两比较上限（>1000 段） | 引擎保留文档序前 1000 段参与比较，超出部分未检，在报告 rationale 与 uncertainty 中声明 |
| 任一脚本异常 | 读 stderr；能修复则修复后重跑（脚本幂等）；不能则保留已有产物，status=partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `diagnosis_report.md` | 六维诊断报告：每条问题含位置/原文锚点/依据/编辑动作/严重度/置信度/复核状态 |
| `edit_plan.json` | 机读编辑动作清单（与 findings 同 id，供逐条勾选采纳/驳回） |
| `findings.json` | 全部问题统一 schema（脚本候选 + Agent 增删后） |
| `redundancy_report.json` | 主攻中间产物：重复对表（两侧位置/quote/相似度/建议处置）、近似重复表、结构性呼应表、句子级跨章重复表、衔接问题表、拆分候选表、统计（冗余字符估算） |
| `result.json` | 契约结果：case_id、status、outputs、evidence_map、change_log、uncertainty、stats |

## 关键方法（详见 references/）

- `references/redundancy_rules.md`：shingle 阈值体系、同段/跨段处置差异、衔接分析判据、拆分触发条件。
- `references/redundancy_taxonomy.md`：段落关系与重复问题分类（完全重复/近似重复/跨章节重复/同义复述/缺过渡/回指悬空/该拆分未拆分）。
- `references/worked_example.md`：完整标注示例（合成稿件，非正式案例）。
- `references/failure_modes.md`：误报来源（摘要与引言天然重叠、方法章标准表述等）与人工复核要点。

## 限制

- 启发式规则面向中英文 IMRaD 类稿件；文学性文本、讲义的重复判据置信度下降（报告中如实标注）。
- 字符 n-gram 对同义改写敏感但对语序重排的检测偏松/偏紧不一；语义级重复（换个说法说同一件事但无共同 n-gram）会漏检——这正是第 7 步 Agent 判断要补的部分。
- 不生成全文改写稿；编辑动作由作者执行（题面"改得动"要求）。
