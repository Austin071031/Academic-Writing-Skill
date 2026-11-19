---
name: grant-rationale-chain
description: 基金申请书写作技能（主攻"立项依据·立得住"）。基于案例材料（原论文、前期成果、组织方 workorder）撰写覆盖七要素的申请书章节稿，立项依据节按"现状（别人做到哪一步）—瓶颈（还差什么）—我们（为什么是我们）"三段必要性论证链组织：脚本先从材料机选三段槽位候选事实（rationale_chain.json），Agent 审定后落稿，机检审计政策口号无证据、现状论断无引用锚定、论证链缺环，全部定位到草稿段并给出修订指令。事实台账（fact_ledger）+ 证据标记语法（〔F0001〕〔拟〕〔确认〕）保证每个数字/引用可回溯、材料外事实零容忍、已完成与拟开展分清。适用于国家自然科学基金等中文申请书核心章节（立项依据/科学问题/研究目标/研究内容/创新点/技术路线/研究基础）的起草与体检；不适用于无科研材料输入的空写场景（如实降级 partial）。输入 /input 下 case.json、task.md、organizer-workorder.json 与材料文件，输出 /app/output 下 proposal_draft.md（清洁章节稿）、proposal_annotated.md（留痕版）、element_mapping.md（七要素对照说明）、rationale_chain.json、report.md、result.json。
---

# 立项依据论证链 · 基金申请书写作 Skill

## 用途与适用条件

对组织方给定科研案例撰写**可直接进入申请书的章节稿＋要素对照说明**，主攻题面"立得住"：
立项依据不是研究意义口号的堆叠，而是一条可复核的必要性论证链——
**现状（别人做到哪一步，逐条锚定已有工作）→ 瓶颈（还差什么，从材料 gap 表述提炼）→ 我们（为什么是我们，锚定申请人已完成前期成果）**。
机制：脚本承担全部机械劳动（材料解析、事实台账、槽位候选机选、口号/锚定/缺环机检、要素覆盖检查、
材料外事实审计、契约组装），Agent 只做三件事——**审定槽位候选、撰写带证据标记的章节稿、处置机检发现**。

适用：有原论文/前期成果/指南类材料的中文基金申请书章节起草与立项依据体检。
不适用：无任何材料输入（按材料缺口如实降级，登记 manual_confirmations）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、可能存在的 `/input/organizer-workorder.json` 与材料文件（md/txt/tex/docx/pdf）；工作目录 `/app/work`；交付目录 `/app/output`。
- 预算：64 次模型请求 / 900 秒。**章节稿按要素逐个落盘（work/sections/），脚本随时可组装部分结果，防超时空手**。
- 本目录即技能根：`scripts/`（管线 13 个脚本）、`references/`（方法判据）、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线（违反即失去正确性分）

1. **不臆造事实**：数字、引用、前期成果、术语只能来自 fact_ledger.json 台账（写作时用〔F0001〕标记锚定）；台账没有的事实禁止写入章节稿。拟开展内容/预期指标必须标〔拟〕；材料不足/冲突标〔确认〕并登记 manual_confirmations。
2. **不伪造核验**：机检发现（findings）逐条复核处置，成立的修订、误报的驳回并写明理由；不得删除 findings 文件充清零。
3. **不空喊口号**："意义重大/国家战略/卡脖子"类表述只允许出现在有〔F〕证据锚定的段落，且须改写为"事实→因此有必要"的论证句式。

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

# 5) 论证链槽位机选：现状/瓶颈/我们三段候选
python3 $S/rationale_engine.py seed --work $W
cat $W/rationale_chain.json
```

**第 6 步（Agent 核心判断①：通读与审定）**。
读 `work/materials_digest.md`（全文 pid 标注摘要）与 `work/rationale_chain.json`：
- 复核 parse_materials 的 role_guess 是否准确（启发式可能误判，误判则心里更正后按正确角色取用事实）；
- 从三段槽位候选中选定可用事实：现状槽选 3-6 条代表性已有工作事实，瓶颈槽归纳 2-3 条关键差距，
  我们槽选与瓶颈呼应的前期成果事实；材料缺口（如我们槽为空）登记 `work/manual_confirmations.json`。

**第 7 步（Agent 核心判断②：分节撰写章节稿）**。按 inspection.json 的 required_elements 逐节写
`work/sections/NN_要素名.md`（NN=01..07；首行 `# 要素名`，如 `# 立项依据`）：
- **证据标记语法（强制）**：材料事实句末标 `〔F0001〕`（FID 必须存在于 fact_ledger.json）；
  拟开展/预期内容标 `〔拟〕`；需人工确认标 `〔确认〕`。
- **立项依据节（本技能主攻）**：严格按 现状→瓶颈→我们 三段组织；现状论断逐条锚定〔F〕；
  瓶颈从材料 gap 表述提炼为可科学回答的差距；我们段只写已完成前期成果并锚定〔F〕；
  段尾用一句话把三段收敛到"因此必须现在开展本研究"。
- 其余六节：科学问题承接瓶颈；研究目标/研究内容/技术路线/考核指标逐条对应；
  创新点写清与具体已有工作的差异（禁用"首次/国际领先/填补空白"）；研究基础区分已完成/拟开展。
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

# 11) 立项依据专项审计：口号无证据/现状无锚定/论证链缺环
python3 $S/rationale_engine.py audit --work $W
cat $W/findings.json
```

**第 12 步（Agent 复核与修订，禁止跳过）**：
1. **删误报**：对照 materials.json 原文复核 source_audit.json、element_findings.json、findings.json
   每条发现；确属误报的在对应文件将该条加 `"status":"已驳回"` 并写理由。
2. **修订**：成立的发现逐条修订 sections 文件（口号改论证句式、补〔F〕锚定、补缺环），
   把每处修改追加到 `work/change_log.json`（{"op","location","before","after","reason"}），
   然后重跑第 8-11 步确认 high 级清零。
3. **标注边界**：材料外但任务必需的常识性内容，标〔拟〕或〔确认〕并在 uncertainty 说明。

```bash
# 13) 报告 + 契约组装 + 发布闸门 + 预览
python3 $S/report_builder.py --work $W --out $O \
    --focus rationale --skill "grant-rationale-chain v1.0.0"
python3 $S/assemble_result.py --work $W --out $O \
    --skill "grant-rationale-chain v1.0.0" --status success   # 有未处置 high/缺材料用 partial
python3 $S/validate_output.py --out $O --work $W    # 必须 PASS
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理（识别并如实记录，不得静默）

| 情况 | 处置 |
|-|-|
| 无材料文件 / 空文件 | 保留骨架，status=failed，exceptions 记录原因 |
| PDF 无 pdftotext 或抽取为空 | exceptions 记录；该文件事实缺失，status≤partial |
| role_guess 误判（指南被判成 prior_work 等） | Agent 按真实角色取用事实；在 uncertainty 注明复核结论 |
| 我们槽无候选（前期成果材料缺失） | 我们段只写"申请人拟依托…"，登记 manual_confirmations，status=partial |
| workorder 与 task.md 要求冲突 | 以 organizer-workorder.json 为准，冲突写入 uncertainty |
| FID 标记指向不存在条目 | draft_builder 报 findings_draft（high）；修正标记后重跑 |
| 超长材料（段落>800） | digest 已截断；优先按槽位候选写作，不必通读全文 |
| 任一脚本异常 | 读 stderr；能修则修后重跑（幂等）；不能则保留已有产物 status=partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `proposal_draft.md` | 清洁章节稿：七要素齐全，可直接粘贴进申请书 |
| `proposal_annotated.md` | 留痕版：段首 D-Pxxx，〔F〕〔拟〕〔确认〕原位保留 |
| `element_mapping.md` | 要素对照说明：七要素×章节×厚度×证据数×状态 + 三级对应清单 |
| `rationale_chain.json` | 论证链三段槽位候选与选用情况（可复用资产） |
| `report.md` | 质量报告：覆盖表、发现分级统计、来源核验统计、异常限制 |
| `preview.html`（+`preview.pdf` 尽力） | 交付预览 |
| `result.json` | 契约结果：case_id、status、outputs、evidence_map、change_log、uncertainty、output_contract 回填 |

## 关键方法（详见 references/）

- `references/rationale_method.md`：三段论证链判据、口号词表与改写句式、锚定规则、误报来源。
- `references/failure_modes.md`：基础 Agent 在立项依据上的典型失败模式与本技能对策。
- `references/worked_example.md`：完整标注示例（合成案例，非正式测试案例）。

## 限制

- 槽位候选基于关键词与角色启发式，低频/隐式 gap 表述可能漏选；Agent 可在第 6 步手工补充。
- 机检只能核对"论断是否有锚点"，不能判断锚定的事实是否真正支撑该论断——语义支撑由第 12 步 Agent 复核保证。
- 口号词表覆盖常见表述，学科特有套话靠 declared 词表扩展（references/rationale_method.md 附录）。
