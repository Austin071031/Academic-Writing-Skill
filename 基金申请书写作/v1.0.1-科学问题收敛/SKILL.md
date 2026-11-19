---
name: grant-question-convergence
description: 基金申请书写作技能（主攻"科学问题收敛"）。基于案例材料（原论文、前期成果、组织方 workorder）撰写覆盖七要素的申请书章节稿，科学问题节按"可回答、可分解、有边界"的收敛判据组织：脚本先从材料 gap/未知信号词机选科学问题候选并给出宽泛表述警示（question_seed.json），Agent 审定后把宽泛研究兴趣收敛为 1-3 个核心问题＋子问题树＋边界声明落稿，机检审计缺节、问题数量过多（>4 未收敛）、无子问题分解、无边界声明、过大表述（系统研究/全面揭示/各个方面/诸方面/全方位/彻底解决）、问题与研究目标·技术路线错位（trigram 相似度双低于阈值），全部定位到草稿段并给出修订指令。事实台账（fact_ledger）+ 证据标记语法（〔F0001〕〔拟〕〔确认〕）保证每个数字/引用可回溯、材料外事实零容忍、已完成与拟开展分清。适用于国家自然科学基金等中文申请书核心章节（立项依据/科学问题/研究目标/研究内容/创新点/技术路线/研究基础）的起草与科学问题体检；不适用于无科研材料输入的空写场景（如实降级 partial）。输入 /input 下 case.json、task.md、organizer-workorder.json 与材料文件，输出 /app/output 下 proposal_draft.md（清洁章节稿）、proposal_annotated.md（留痕版）、element_mapping.md（七要素对照说明）、question_seed.json、report.md、result.json。
---

# 科学问题收敛 · 基金申请书写作 Skill

## 用途与适用条件

对组织方给定科研案例撰写**可直接进入申请书的章节稿＋要素对照说明**，主攻题面"科学问题收敛"：
科学问题不是研究兴趣的罗列，而是把宽泛兴趣**收敛为可回答、可分解、有边界的科学问题**——
**候选（从材料 gap/未知表述机选）→ 收敛（1-3 个核心问题，拒绝"系统研究/全面揭示"式过大表述）→
分解（核心问题→子问题→任务的问题树）→ 边界（聚焦什么、不涉及什么）→ 对齐（与研究目标、技术路线同词同向）**。
机制：脚本承担全部机械劳动（材料解析、事实台账、问题候选机选、收敛五规则机检、要素覆盖检查、
材料外事实审计、契约组装），Agent 只做三件事——**审定问题候选、撰写带证据标记的章节稿、处置机检发现**。

适用：有原论文/前期成果/指南类材料的中文基金申请书章节起草与科学问题收敛体检。
不适用：无任何材料输入（按材料缺口如实降级，登记 manual_confirmations）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、可能存在的 `/input/organizer-workorder.json` 与材料文件（md/txt/tex/docx/pdf）；工作目录 `/app/work`；交付目录 `/app/output`。
- 预算：64 次模型请求 / 900 秒。**章节稿按要素逐个落盘（work/sections/），脚本随时可组装部分结果，防超时空手**。
- 本目录即技能根：`scripts/`（管线 13 个脚本）、`references/`（方法判据）、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线（违反即失去正确性分）

1. **不臆造事实**：数字、引用、前期成果、术语只能来自 fact_ledger.json 台账（写作时用〔F0001〕标记锚定）；台账没有的事实禁止写入章节稿。拟开展内容/预期指标必须标〔拟〕；材料不足/冲突标〔确认〕并登记 manual_confirmations。
2. **不伪造核验**：机检发现（findings）逐条复核处置，成立的修订、误报的驳回并写明理由；不得删除 findings 文件充清零。
3. **不写过大问题**："系统研究/全面揭示/各个方面/诸方面/全方位/彻底解决"类表述禁止出现在科学问题节；科学问题必须是单一机制/对象明确的可回答问句，且带边界声明（聚焦/限定/不涉及）。

## 标准工作流（严格按序执行）

```bash
SKILL_DIR=/skills/weekly-skill   # 平台安装路径
W=/app/work; O=/app/output; mkdir -p $W $O
S=$SKILL_DIR/scripts

# 1) 兜底骨架（防超时空手；幂等）
python3 $S/init_result.py

# 2) 案例侦察：case_id、七要素要求、output_contract、材料清单、workorder 约束
python3 $S/inspect_case.py --work $W
cat $W/inspection.json        # 重点看 required_elements、deliverable_hints、issues

# 3) 材料解析：段落稳定 ID + 角色猜测（paper/prior_work/guide/data）
python3 $S/parse_materials.py --work $W

# 4) 事实台账：数字/引用/成果/术语逐条登记 FID + 来源坐标
python3 $S/fact_ledger.py --work $W

# 5) 科学问题候选机选 + 宽泛表述警示
python3 $S/question_engine.py seed --work $W
cat $W/question_seed.json
```

**第 6 步（Agent 核心判断①：通读与收敛）**。
读 `work/materials_digest.md`（全文 pid 标注摘要）与 `work/question_seed.json`：
- 复核 parse_materials 的 role_guess 是否准确（启发式可能误判，误判则心里更正后按正确角色取用事实）；
- 从 candidates 中归纳 1-3 个可回答的核心科学问题方向：优先选择有前期成果呼应、能被本课题
  方法闭环回答的 gap；把每个核心问题预分解为 2-4 个子问题，并预先想好边界（不涉及什么）；
- warnings 中的宽泛表述（材料原文或 task.md 口吻）是**反面清单**：写作时必须收敛，不得照抄；
- 材料缺口（如材料中没有任何 gap/未知表述，candidates 为空）登记 `work/manual_confirmations.json`。

**第 7 步（Agent 核心判断②：分节撰写章节稿）**。按 inspection.json 的 required_elements 逐节写
`work/sections/NN_要素名.md`（NN=01..07；首行 `# 要素名`，如 `# 科学问题`）：
- **证据标记语法（强制）**：材料事实句末标 `〔F0001〕`（FID 必须存在于 fact_ledger.json）；
  拟开展/预期内容标 `〔拟〕`；需人工确认标 `〔确认〕`。
- **科学问题节（本技能主攻）**：1-3 个核心问题，每个写成以"？/？"结尾的可回答问句
  （机制/定量关系/构效关系型，而非领域工程型）；每个核心问题用「其一/其二…」或「（1）（2）」
  分解为子问题；节内必须有边界声明（本课题聚焦于…，不涉及…，限定于…）；问题关键词
  （对象/机制/方法）须能在研究目标与技术路线中复现。
- 其余六节：立项依据的现状—瓶颈为科学问题提供支点；研究目标/研究内容/技术路线逐条
  承接子问题；创新点写清与具体已有工作的差异（禁用"首次/国际领先/填补空白"）；
  研究基础区分已完成/拟开展。
- 厚度：以 inspection.deliverable_hints 与 workorder 字数要求为准；缺省立项依据≥400 字、
  技术路线/研究基础≥300 字、其余≥150 字（elements_check 机检）。
- **预算兜底**：模型请求过半仍未写完，立即跳到第 8 步交付 partial，已写节照样组装。

```bash
# 8) 组装章节稿（清洁版 + 留痕版 + 要素对照说明）+ FID 存在性校验
python3 $S/draft_builder.py --work $W --out $O

# 9) 材料外事实审计（数字/引用必须台账可查）
python3 $S/source_audit.py --work $W

# 10) 七要素覆盖与厚度检查 + 三级对应表
python3 $S/elements_check.py --work $W --out $O

# 11) 科学问题专项审计：缺节/数量未收敛/无分解/无边界/过大/错位
python3 $S/question_engine.py audit --work $W
cat $W/findings.json
```

**第 12 步（Agent 复核与修订，禁止跳过）**：
1. **删误报**：对照 materials.json 原文复核 source_audit.json、element_findings.json、findings.json
   每条发现；确属误报的在对应文件将该条加 `"status":"已驳回"` 并写理由。
2. **修订**：成立的发现逐条修订 sections 文件（过大表述改写为可回答问句、补子问题分解、
   补边界声明、对齐目标/路线关键词），把每处修改追加到 `work/change_log.json`
   （{"op","location","before","after","reason"}），然后重跑第 8-11 步确认 high 级清零。
3. **标注边界**：材料外但任务必需的常识性内容，标〔拟〕或〔确认〕并在 uncertainty 说明。

```bash
# 13) 报告 + 契约组装 + 发布闸门 + 预览
python3 $S/report_builder.py --work $W --out $O \
    --focus question --skill "grant-question-convergence v1.0.1"
python3 $S/assemble_result.py --work $W --out $O \
    --skill "grant-question-convergence v1.0.1" --status success   # 有未处置 high/缺材料用 partial
python3 $S/validate_output.py --out $O --work $W    # 必须 PASS
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理（识别并如实记录，不得静默）

| 情况 | 处置 |
|-|-|
| 无材料文件 / 空文件 | 保留骨架，status=failed，exceptions 记录原因 |
| PDF 无 pdftotext 或抽取为空 | exceptions 记录；该文件事实缺失，status≤partial |
| role_guess 误判（指南被判成 prior_work 等） | Agent 按真实角色取用事实；在 uncertainty 注明复核结论 |
| 问题候选为空（材料无 gap/未知信号词） | 科学问题从立项依据瓶颈归纳，登记 manual_confirmations，status=partial |
| task.md 本身含宽泛表述（如"系统研究…"） | seed 已在 warnings 警示；写作时收敛改写，冲突口径写入 uncertainty |
| workorder 与 task.md 要求冲突 | 以 organizer-workorder.json 为准，冲突写入 uncertainty |
| FID 标记指向不存在条目 | draft_builder 报 findings_draft（high）；修正标记后重跑 |
| method_misaligned 疑似误报（措辞差异大但语义一致） | 在科学问题节复现目标/路线的核心关键词（对象/机制/方法），或在 findings 标"已驳回"并写理由 |
| 超长材料（段落>800） | digest 已截断；优先按问题候选写作，不必通读全文 |
| 任一脚本异常 | 读 stderr；能修则修后重跑（幂等）；不能则保留已有产物 status=partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `proposal_draft.md` | 清洁章节稿：七要素齐全，可直接粘贴进申请书 |
| `proposal_annotated.md` | 留痕版：段首 D-Pxxx，〔F〕〔拟〕〔确认〕原位保留 |
| `element_mapping.md` | 要素对照说明：七要素×章节×厚度×证据数×状态 + 三级对应清单 |
| `question_seed.json` | 科学问题候选（gap/未知信号词上下文）与宽泛表述警示（可复用资产） |
| `report.md` | 质量报告：覆盖表、发现分级统计、来源核验统计、异常限制 |
| `preview.html`（+`preview.pdf` 尽力） | 交付预览 |
| `result.json` | 契约结果：case_id、status、outputs、evidence_map、change_log、uncertainty、output_contract 回填 |

## 关键方法（详见 references/）

- `references/question_method.md`：收敛三判据（可回答/可分解/有边界）、问题树写法、
  过大表述词表、问题—目标—方法对齐判据、误报来源。
- `references/failure_modes.md`：基础 Agent 在科学问题上的典型失败模式与本技能对策。
- `references/worked_example.md`：完整标注示例（合成案例，非正式测试案例）。

## 限制

- 问题候选基于 gap/未知信号词启发式，低频/隐式 gap 表述可能漏选；Agent 可在第 6 步手工补充。
- 问题计数按"？/？"结尾句与编号条目取较大者，混合写法或问句嵌在陈述句中可能低估；Agent 复核。
- 错位判定基于字符 trigram 相似度，只核对"关键词是否复现"，不能判断语义是否真正对齐——
  语义对齐由第 12 步 Agent 复核保证。
- 过大表述词表覆盖常见表述，学科特有的宏大套话靠 declared 词表扩展
  （references/question_method.md 附录）。
