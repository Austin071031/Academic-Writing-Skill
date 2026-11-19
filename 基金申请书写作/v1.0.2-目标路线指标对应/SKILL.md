---
name: grant-alignment-matrix
description: 基金申请书写作技能（主攻"对得上：研究目标、研究内容、技术路线与考核指标逐条对应，不出现目标三个、路线两条、指标另说一套"）。基于案例材料（原论文、前期成果、组织方 workorder）撰写覆盖七要素的申请书章节稿；专属引擎 alignment_engine 先从草稿四节机选编号条目并打印计数（seed，供写作前自查条目数设计），落稿后再建跨节相似度矩阵与编号互引图谱（audit）：每个研究目标≥1 条研究内容对应、每条研究内容≥1 条技术路线支撑、每条考核指标可回溯≥1 个研究目标，孤儿条目与四节数量不一致（count_mismatch，写明"目标 3 条、路线 2 条"式事实）、缺节逐一定位并给出修订指令，另输出 alignment_table.md 对应关系总表。事实台账（fact_ledger）+ 证据标记语法（〔F0001〕〔拟〕〔确认〕）保证每个数字/引用可回溯、材料外事实零容忍。适用于国家自然科学基金等中文申请书核心章节（立项依据/科学问题/研究目标/研究内容/创新点/技术路线/研究基础，含考核指标节）的起草与一致性体检；不适用于无科研材料输入的空写场景（如实降级 partial）。输入 /input 下 case.json、task.md、organizer-workorder.json 与材料文件，输出 /app/output 下 proposal_draft.md（清洁章节稿）、proposal_annotated.md（留痕版）、element_mapping.md（七要素对照说明）、alignment_table.md（四节对应矩阵表）、report.md、result.json。
---

# 目标—内容—路线—指标对应 · 基金申请书写作 Skill

## 用途与适用条件

对组织方给定科研案例撰写**可直接进入申请书的章节稿＋要素对照说明**，主攻题面"对得上"：
评审最敏感的一致性硬伤是**研究目标、研究内容、技术路线、考核指标四节各说各话——
目标列了三条、技术路线只写两条、考核指标另起一套口径**。
本技能机制：脚本承担全部机械劳动（材料解析、事实台账、四节编号条目机选、跨节相似度矩阵、
编号互引识别、孤儿/数量不一致/缺节机检、对应关系总表、契约组装），Agent 只做三件事——
**设计四节条目数并自查、撰写带证据标记且逐条对应的章节稿、处置机检发现**。

适用：有原论文/前期成果/指南类材料的中文基金申请书章节起草与"目标—内容—路线—指标"
一致性体检。
不适用：无任何材料输入（按材料缺口如实降级，登记 manual_confirmations）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、可能存在的 `/input/organizer-workorder.json` 与材料文件（md/txt/tex/docx/pdf）；工作目录 `/app/work`；交付目录 `/app/output`。
- 预算：64 次模型请求 / 900 秒。**章节稿按要素逐个落盘（work/sections/），脚本随时可组装部分结果，防超时空手**。
- 本目录即技能根：`scripts/`（管线 13 个脚本）、`references/`（方法判据）、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线（违反即失去正确性分）

1. **不臆造事实**：数字、引用、前期成果、术语只能来自 fact_ledger.json 台账（写作时用〔F0001〕标记锚定）；台账没有的事实禁止写入章节稿。拟开展内容/预期指标必须标〔拟〕；材料不足/冲突标〔确认〕并登记 manual_confirmations。
2. **不伪造核验**：机检发现（findings）逐条复核处置，成立的修订、误报的驳回并写明理由；不得删除 findings 文件充清零。
3. **对应不失真**：研究目标、研究内容、技术路线、考核指标四节条目数量一致且逐条对应；count_mismatch / missing_section 未处置不得交付 success；不得交付"目标三个、路线两条、指标另说一套"的草稿。

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

# 5) 条目设计自查（写作前）：首次运行打印条目设计指引；
#    写完 sections 并跑过 draft_builder 后重跑本步，打印四节条目计数供自查
python3 $S/alignment_engine.py seed --work $W
cat $W/alignment_seed.json    # sections/counts/notes
```

**第 6 步（Agent 核心判断①：通读材料与条目设计）**。
读 `work/materials_digest.md`（全文 pid 标注摘要）与 `work/inspection.json`：
- 复核 parse_materials 的 role_guess 是否准确（启发式可能误判，误判则心里更正后按正确角色取用事实）；
- **设计四节条目数（本技能主攻）**：依据科学问题分解确定研究目标条数 n（建议 2-4 条），
  研究内容、技术路线、考核指标均按同一 n 设计，做到 目标↔内容↔路线↔指标 一一对应；
  条目编号体例四节统一（推荐：目标一/二/三、（一）（二）（三）、步骤一/二/三、指标一/二/三，
  均置于行首；体例判据见 references/alignment_method.md）；
- 材料缺口登记 `work/manual_confirmations.json`。

**第 7 步（Agent 核心判断②：分节撰写章节稿）**。按 inspection.json 的 required_elements 逐节写
`work/sections/NN_要素名.md`（NN=01..08；首行 `# 要素名`，如 `# 研究目标`、`# 考核指标`）：
- **证据标记语法（强制）**：材料事实句末标 `〔F0001〕`（FID 必须存在于 fact_ledger.json）；
  拟开展/预期内容标 `〔拟〕`；需人工确认标 `〔确认〕`。
- **四节对应（本技能主攻）**：研究目标/研究内容/技术路线/考核指标逐节逐条编号；
  每条研究内容开头显式呼应目标（如"（一）偶极取向调控机制研究：支撑目标一……"），
  每条技术路线写明"步骤X：针对研究内容（X）……"，每条考核指标写明"指标X：对应目标X……"
  且预期指标一律标〔拟〕；**指标值不许另起炉灶，必须与目标同源**。
- 其余各节：立项依据按 现状→瓶颈→我们 组织并逐条锚定〔F〕；科学问题承接瓶颈；
  创新点写清与具体已有工作的差异（禁用"首次/国际领先/填补空白"）；研究基础区分已完成/拟开展。
- 厚度：以 inspection.deliverable_hints 与 workorder 字数要求为准；缺省立项依据≥400 字、
  技术路线/研究基础≥300 字、其余≥150 字（elements_check 机检）。
- **预算兜底**：模型请求过半仍未写完，立即跳到第 8 步交付 partial，已写节照样组装。

```bash
# 8) 组装章节稿（清洁版 + 留痕版 + 要素对照说明）+ FID 存在性校验
python3 $S/draft_builder.py --work $W --out $O
#    落稿后重跑一次 seed，确认四节条目计数与设计一致
python3 $S/alignment_engine.py seed --work $W

# 9) 材料外事实审计（数字/引用必须台账可查）
python3 $S/source_audit.py --work $W

# 10) 七要素覆盖与厚度检查 + 三级对应表
python3 $S/elements_check.py --work $W --out $O

# 11) 对应矩阵专项审计：孤儿条目/数量不一致/缺节 + 对应关系总表
python3 $S/alignment_engine.py audit --work $W --out $O
cat $W/findings.json
cat $O/alignment_table.md
```

**第 12 步（Agent 复核与修订，禁止跳过）**：
1. **删误报**：对照 materials.json 原文复核 source_audit.json、element_findings.json、findings.json
   每条发现；孤儿条目若系同义改写导致低相似的误报，在对应文件将该条加 `"status":"已驳回"`
   并写理由。
2. **修订**：成立的发现逐条修订 sections 文件（补齐孤儿条目、对齐条目数、统一编号体例、
   在路线/指标条目中显式引用内容/目标编号），把每处修改追加到 `work/change_log.json`
   （{"op","location","before","after","reason"}），然后重跑第 8-11 步确认 high 级清零。
3. **标注边界**：材料外但任务必需的常识性内容，标〔拟〕或〔确认〕并在 uncertainty 说明。

```bash
# 13) 报告 + 契约组装 + 发布闸门 + 预览
python3 $S/report_builder.py --work $W --out $O \
    --focus alignment --skill "grant-alignment-matrix v1.0.2"
python3 $S/assemble_result.py --work $W --out $O \
    --skill "grant-alignment-matrix v1.0.2" --status success   # 有未处置 high/缺材料用 partial
python3 $S/validate_output.py --out $O --work $W    # 必须 PASS
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理（识别并如实记录，不得静默）

| 情况 | 处置 |
|-|-|
| 无材料文件 / 空文件 | 保留骨架，status=failed，exceptions 记录原因 |
| PDF 无 pdftotext 或抽取为空 | exceptions 记录；该文件事实缺失，status≤partial |
| 草稿缺考核指标节（missing_section high） | 补写 `NN_考核指标.md`（首行 `# 考核指标`），指标逐条回溯目标并标〔拟〕，重跑第 8/11 步 |
| 编号体例混乱（引擎按段落整体切条并记 note） | 统一为行首编号（目标一/（一）/步骤一/指标一）后重跑 draft_builder 与 audit |
| 同义改写致低相似、孤儿误报（orphan_* medium） | Agent 复核：确有对应的驳回并写理由；建议同时在条目中显式引用对方编号消除歧义 |
| 目标/内容/路线数量不一致（count_mismatch high） | 按 finding 写明的事实增删条目，使四节一一对应后重跑 |
| FID 标记指向不存在条目 | draft_builder 报 findings_draft（high）；修正标记后重跑 |
| workorder 与 task.md 要求冲突 | 以 organizer-workorder.json 为准，冲突写入 uncertainty |
| 超长材料（段落>800） | digest 已截断；优先按要素写作，不必通读全文 |
| 任一脚本异常 | 读 stderr；能修则修后重跑（幂等）；不能则保留已有产物 status=partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `proposal_draft.md` | 清洁章节稿：要素齐全、四节逐条对应，可直接粘贴进申请书 |
| `proposal_annotated.md` | 留痕版：段首 D-Pxxx，〔F〕〔拟〕〔确认〕原位保留 |
| `element_mapping.md` | 要素对照说明：要素×章节×厚度×证据数×状态 + 三级对应清单 |
| `alignment_table.md` | 四节条目×对应关系总表（以研究目标为锚）+ 条目清单 + 审计发现 |
| `alignment_seed.json` / `alignment_matrix.json` | 四节条目机选/相似度矩阵/覆盖关系/发现（work/ 下，可复用资产） |
| `report.md` | 质量报告：覆盖表、发现分级统计、来源核验统计、异常限制 |
| `preview.html`（+`preview.pdf` 尽力） | 交付预览 |
| `result.json` | 契约结果：case_id、status、outputs、evidence_map、change_log、uncertainty、output_contract 回填 |

## 关键方法（详见 references/）

- `references/alignment_method.md`：条目编号规范、对应矩阵判据（相似度阈值 0.12 + 编号互引）、覆盖规则、阈值依据、误报来源。
- `references/failure_modes.md`：基础 Agent 在四节对应上的典型失败模式与本技能对策。
- `references/worked_example.md`：完整标注示例（3 目标-3 内容-3 路线-3 指标全对应通过 + 反例命中；合成案例，非正式测试案例）。

## 限制

- 相似度对应基于字符 3-gram 词汇重叠，同义改写大的对应条目可能低于阈值 0.12 而报孤儿
  （候选误报）；编号互引规则可消解显式引用情形，其余由第 12 步 Agent 复核兜底。
- 条目切分依赖行首编号体例；编号连写在同一行（"目标一…目标二…"不换行）时只切出一条，
  引擎记 note 提示，Agent 应改为行首编号。
- 考核指标节识别依赖 element 命名（考核指标/预期成果）或研究目标节内含 指标/考核/预期 信号；
  其他命名（如"验收标准"）需 Agent 改名或在 uncertainty 说明。
- 机检查"条目是否对应"，不判断对应关系在科学上是否合理（目标与内容是否真正同口径），
  语义合理性由第 12 步 Agent 复核保证。
