---
name: section-narrative-flow
description: 论文结构诊断技能（主攻"章节结构与叙事顺序"）。对完整稿件做六维结构普查（研究问题/章节结构/论证链/段落关系/重复内容/结论边界），并深度核验章节角色序列是否符合论证顺序、核心章节是否缺失、篇幅是否失衡、标题层级是否跳变、缩写与回指的信息释放顺序是否服务读者。v2.0.0 单点强化：复核闭环主通道——review_helper 将全部候选问题连同原文上下文打包供一次性逐条裁决（采纳/修正/驳回+理由），总体诊断与裁决结论回写报告，保证每条结论都经 Agent 原文对照。所有问题定位到章节/段落/句子并附原文锚点与可执行编辑动作（非改写稿）。当用户要求检查论文章节顺序、叙事逻辑、结构重组、缩写规范、篇幅分配时使用；输入为 /input 下稿件（md/txt/tex/docx/pdf）与 case.json，输出 /app/output 下 diagnosis_report.md、edit_plan.json、findings.json、section_map.json、restructured_outline.md、result.json。
---

# 章节结构与叙事顺序 · 结构诊断 Skill

## 用途与适用条件

对一篇**完整稿件**执行结构诊断，交付作者可直接执行的编辑计划。主攻维度：**章节结构与叙事顺序**（角色序列、篇幅、层级、信息释放顺序）；同时用六维普查保证覆盖面（评分与复核都要求不缺维度）。

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

# 5) 主攻引擎：角色序列逆序对、核心章节缺失、篇幅表、缩写/回指信息释放（section_map.json）
python3 $S/section_flow.py --work $W
cat $W/section_map.json            # 重点阅读 role_sequence / inversions / abbrev_table
cat $W/restructured_outline.md     # 重组大纲草稿（各节去向 + 动作汇总）

# 6) 生成可交付草稿：diagnosis_report.md + edit_plan.json + findings.json
python3 $S/report_builder.py --work $W --out $O \
    --focus section_structure --skill "section-narrative-flow v2.0.0"

# 6.5) 复核打包：全部候选问题 + 原文上下文一次成文（本版核心）
python3 $S/review_helper.py --work $W --out $O pack
```

## 第 7 步：复核闭环（本技能的核心增值，禁止跳过，预算表见下）

**必须**读取 `$W/review_pack.md`（每条候选问题附 ±1 段原文上下文，一次读取即可完成全部裁决），
对照 `$W/adjudication_template.json` 的格式写出 `$W/adjudications.json`：

1. **逐条裁决**：每条给出 `verdict ∈ {采纳, 修正, 驳回}` + 一句 `reason`（指回原文上下文）；
   修正时在 `revision` 中给出改后的 type/severity/action。**驳回即删除**，只保留你核对原文后
   确信成立或修正后成立的问题。尤其注意：期刊模板要求"结果在方法前"的逆序对（非缺陷）、
   综述类文体缺方法/结果章（非缺陷）、标题同名但职责不同的章节（非合并候选）。
2. **总体诊断**：在 `overall_diagnosis` 写 3-5 句（主要问题在哪个维度、为什么、先改什么）；
   在 `dimension_main_issues` 为六维各写一句主问题判定（无问题则写"未检出实质问题"）。
3. **补漏报**：通读 `$W/structure.json` 章节清单与 `$W/section_map.json`，若发现脚本未捕获的
   **真实**断裂，按 findings schema 手工追加进 `$O/findings.json`（每条必须有原文锚点，
   禁止虚构），并在 adjudications.json 中给一条 `verdict=采纳` 记录。

然后回填并重新生成交付物：

```bash
python3 $S/review_helper.py --work $W --out $O apply \
    --adjudications $W/adjudications.json
# 注意：apply 后请重新运行第 6 步 report_builder 之前的产物不变；
# apply 已直接更新 findings.json 并把"0.5 总体诊断与裁决结论"写入报告头部。
```

**预算表（64 请求 / 900 秒，超预算风险时按此取舍）**

| 步骤 | 模型请求 | 说明 |
|-|-|-|
| 步骤 1-6.5（脚本） | ~8 | 全部为脚本调用与简短输出阅读 |
| 读 review_pack + 写 adjudications | 2-4 | 长稿件 review_pack 较大时可分两次读 |
| 补漏报（可选） | 0-4 | 预算紧张时至少覆盖主攻维度 |
| apply + assemble + validate | ~3 | 脚本调用 |
| 余量 | ≥40 | 异常处理与重跑 |

编辑动作只允许这 9 类：`move / merge / split / narrow / qualify / add / add_transition / add_limitation / reorder`。**不产出另起炉灶的改写稿**。

## 第 8 步：交付与闸门

```bash
# 状态诚实：全部完成=success；材料缺口/部分维度无法判断=partial（在 uncertainty 写明）
python3 $S/assemble_result.py --work $W --out $O \
    --skill "section-narrative-flow v2.0.0" --status success
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
| 稿件疑似截断 | parse 已检测；顺序/结论类条目全部标"需人工确认" |
| 全文仅 1-2 节（短文/摘要体） | 核心缺失降级为 low 提示，注明"短文档降级" |
| 综述类文体缺方法/结果章 | 引擎自动豁免对应缺失项；其余维度照常 |
| 无参考文献/图表 | 不报错；论证链维度相应条目注明"证据锚点类型受限" |
| 任一脚本异常 | 读 stderr；能修复则修复后重跑（脚本幂等）；不能则保留已有产物，status=partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `diagnosis_report.md` | 六维诊断报告：每条问题含位置/原文锚点/依据/编辑动作/严重度/置信度/复核状态 |
| `edit_plan.json` | 机读编辑动作清单（与 findings 同 id，供逐条勾选采纳/驳回） |
| `findings.json` | 全部问题统一 schema（脚本候选 + Agent 增删后） |
| `section_map.json` | 角色序列表（含逆序对）、篇幅占比表、缩写首现表（可复核中间产物） |
| `restructured_outline.md` | 重组大纲草稿：现状序列 → 建议叙事顺序（各节去向 + move/merge/split/add 汇总） |
| `work/review_pack.md` | 复核包：每条候选问题 + ±1 段原文上下文（Agent 第 7 步唯一必读） |
| `work/adjudications.json` | Agent 裁决结果：逐条 采纳/修正/驳回 + 理由 + 总体诊断（回写报告 0.5 节） |
| `result.json` | 契约结果：case_id、status、outputs、evidence_map、change_log、uncertainty、stats |

## 关键方法（详见 references/）

- `references/structure_rules.md`：角色归类、规范顺序、篇幅阈值、缩写首现规则的判据说明。
- `references/section_taxonomy.md`：章节类问题分类（顺序倒置/核心缺失/篇幅失衡/层级跳变/信息过早释放/该合并未合并/该拆分未拆分）。
- `references/worked_example.md`：完整标注示例（合成稿件，非正式案例）。
- `references/failure_modes.md`：误报来源与人工复核要点。

## 限制

- 启发式规则面向中英文 IMRaD 类稿件；文学性文本、讲义、纯综述的序列判定置信度下降（报告中如实标注）。
- 角色归类依赖标题关键词；标题写法刁钻（如"我们的办法"）会归入 other 而漏检——这正是第 7 步 Agent 判断要补的部分。
- 不生成全文改写稿；编辑动作由作者执行（题面"改得动"要求）。
