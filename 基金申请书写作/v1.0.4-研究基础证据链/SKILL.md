---
name: grant-feasibility-evidence
description: 基金申请书写作技能（主攻"研究基础·查得到"）。基于案例材料（原论文、前期成果、组织方 workorder）撰写覆盖七要素的申请书章节稿，研究基础与可行性节按"能力—证据—与本研究关系"三列证据链组织：脚本先从材料机选证据链行（prior_work 角色文件段落及含申请人/本团队/平台/实验室信号的段落，能力短语+证据 FID 自动填好、关系列留空），Agent 审定后另存 evidence_chain.json 并逐行填写与本研究的关系，落稿后机检审计：拟开展内容写成了已完成体（〔拟〕段落体貌判 completed→high）、已完成成果写成了拟开展体（成果类〔F〕段落体貌判 planned→medium）、成果断言无〔F〕来源锚定（high）、证据链关系列空缺（medium）、可行性信号缺失（low），全部定位到草稿段并给出修订指令。事实台账（fact_ledger）+ 证据标记语法（〔F0001〕〔拟〕〔确认〕）保证每条成果追溯到具体来源、材料外事实零容忍、已完成与拟开展分清。适用于国家自然科学基金等中文申请书核心章节（立项依据/科学问题/研究目标/研究内容/创新点/技术路线/研究基础与可行性）的起草与体检；不适用于无科研材料输入的空写场景（如实降级 partial）。输入 /input 下 case.json、task.md、organizer-workorder.json 与材料文件，输出 /app/output 下 proposal_draft.md（清洁章节稿）、proposal_annotated.md（留痕版）、element_mapping.md（七要素对照说明）、evidence_chain.json、report.md、result.json。
---

# 研究基础证据链 · 基金申请书写作 Skill

## 用途与适用条件

对组织方给定科研案例撰写**可直接进入申请书的章节稿＋要素对照说明**，主攻题面"查得到"：
研究基础不是简历式成果罗列，而是一条可逐条回溯的**证据链**——
**能力（我们会什么）→ 证据（凭什么说会，锚定具体论文/专利/项目/平台事实）→ 与本研究的关系（这条基础支撑本课题哪一步）**，
且已完成前期成果与拟开展内容在体貌上严格分清。
机制：脚本承担全部机械劳动（材料解析、事实台账、证据链行机选、体貌/锚定/链完整性机检、要素覆盖检查、
材料外事实审计、契约组装），Agent 只做三件事——**审定证据链行并填写关系列、撰写带证据标记的章节稿、处置机检发现**。

适用：有原论文/前期成果/指南类材料的中文基金申请书章节起草与研究基础节体检。
不适用：无任何材料输入（按材料缺口如实降级，登记 manual_confirmations）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、可能存在的 `/input/organizer-workorder.json` 与材料文件（md/txt/tex/docx/pdf）；工作目录 `/app/work`；交付目录 `/app/output`。
- 预算：64 次模型请求 / 900 秒。**章节稿按要素逐个落盘（work/sections/），脚本随时可组装部分结果，防超时空手**。
- 本目录即技能根：`scripts/`（管线 13 个脚本）、`references/`（方法判据）、`docs/USAGE.md`、`examples/minimal_example.md`。

## 三条红线（违反即失去正确性分）

1. **不臆造事实**：数字、引用、前期成果、平台条件只能来自 fact_ledger.json 台账（写作时用〔F0001〕标记锚定）；台账没有的事实禁止写入章节稿。拟开展内容/预期指标必须标〔拟〕；材料不足/冲突标〔确认〕并登记 manual_confirmations。
2. **不伪造核验**：机检发现（findings）逐条复核处置，成立的修订、误报的驳回并写明理由；不得删除 findings 文件充清零。
3. **不混淆体貌**：已完成前期成果一律用完成体（已发表/已获授权/已建立）并带〔F〕；本课题拟开展内容一律用拟态（拟/将/预期）并带〔拟〕；两者不得互相借体——〔拟〕段落出现"已/了/获得/建立"即属事实性错误。

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

# 5) 证据链行机选：能力—证据两列初稿（关系列留空）
python3 $S/feasibility_engine.py seed --work $W
cat $W/evidence_chain_seed.json
```

**第 6 步（Agent 核心判断①：通读与审定证据链）**。
读 `work/materials_digest.md`（全文 pid 标注摘要）与 `work/evidence_chain_seed.json`：
- 复核 parse_materials 的 role_guess 是否准确（启发式可能误判，误判则心里更正后按正确角色取用事实）；
- 从机选行中选定可用行：每行核对 capability 短语是否概括准确（可按原文改写）、evidence_fids 是否真正支撑该能力；
- **逐行填写 `relation_to_project`**：写明该能力/证据支撑本课题哪个研究内容或技术路线步骤；
  与本研究无关的行整行删除；材料中重要但漏选的基础可手工增行（fid 必须存在于台账）；
- 审定结果**另存为 `work/evidence_chain.json`**（勿改动 seed 文件，seed 留作机选初稿对照）；
- 材料缺口（如无任何前期成果行）登记 `work/manual_confirmations.json`。

**第 7 步（Agent 核心判断②：分节撰写章节稿）**。按 inspection.json 的 required_elements 逐节写
`work/sections/NN_要素名.md`（NN=01..07；首行 `# 要素名`，如 `# 研究基础与可行性`）：
- **证据标记语法（强制）**：材料事实句末标 `〔F0001〕`（FID 必须存在于 fact_ledger.json）；
  拟开展/预期内容标 `〔拟〕`；需人工确认标 `〔确认〕`。
- **研究基础与可行性节（本技能主攻）**：按证据链行组织，每条基础写成
  "已完成成果〔F〕→ 因此具备 X 能力 → 支撑本研究 Y"的三段式；
  成果断言（论文/专利/项目/平台/奖项/发表/授权/结题）必须逐条带〔F〕；
  拟开展内容（拟建平台、拟开展验证）必须标〔拟〕且句中不得出现完成信号词；
  节内须明确覆盖可行性论证（平台条件、团队分工、技术保障至少其一）。
- 其余六节：立项依据按"现状—瓶颈—我们"论证；科学问题聚焦 1-3 个并可分解；
  研究目标/研究内容/技术路线/考核指标逐条对应；创新点写清与具体已有工作的差异
  （禁用"首次/国际领先/填补空白"）。
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

# 11) 研究基础专项审计：体貌冲突/成果无锚定/证据链缺列/可行性缺失
python3 $S/feasibility_engine.py audit --work $W
cat $W/findings.json
```

**第 12 步（Agent 复核与修订，禁止跳过）**：
1. **删误报**：对照 materials.json 原文复核 source_audit.json、element_findings.json、findings.json
   每条发现；确属误报的在对应文件将该条加 `"status":"已驳回"` 并写理由。
2. **修订**：成立的发现逐条修订 sections 文件（拟开展改拟态、已完成改完成体、补〔F〕锚定、
   补填 relation_to_project），把每处修改追加到 `work/change_log.json`
   （{"op","location","before","after","reason"}），然后重跑第 8-11 步确认 high 级清零。
3. **标注边界**：材料外但任务必需的常识性内容，标〔拟〕或〔确认〕并在 uncertainty 说明。

```bash
# 13) 报告 + 契约组装 + 发布闸门 + 预览
python3 $S/report_builder.py --work $W --out $O \
    --focus feasibility --skill "grant-feasibility-evidence v1.0.4"
python3 $S/assemble_result.py --work $W --out $O \
    --skill "grant-feasibility-evidence v1.0.4" --status success   # 有未处置 high/缺材料用 partial
python3 $S/validate_output.py --out $O --work $W    # 必须 PASS
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理（识别并如实记录，不得静默）

| 情况 | 处置 |
|-|-|
| 无材料文件 / 空文件 | 保留骨架，status=failed，exceptions 记录原因 |
| PDF 无 pdftotext 或抽取为空 | exceptions 记录；该文件事实缺失，status≤partial |
| role_guess 误判（指南被判成 prior_work 等） | Agent 按真实角色取用事实；seed 行来源以复核后角色为准，在 uncertainty 注明复核结论 |
| seed 无证据链行（前期成果材料缺失） | 研究基础节只写"申请人拟依托…"并标〔拟〕，登记 manual_confirmations，status=partial |
| evidence_chain.json 未另存 | audit 报 low 提示；补审定流程后重跑，不得直接改 seed 文件冒充审定版 |
| workorder 与 task.md 要求冲突 | 以 organizer-workorder.json 为准，冲突写入 uncertainty |
| FID 标记指向不存在条目 | draft_builder 报 findings_draft（high）；修正标记后重跑 |
| 段落同时含已完成与拟开展内容 | aspect_classify 判 mixed 不命中体貌规则；建议拆段，一段一体貌 |
| 超长材料（段落>800） | digest 已截断；优先按证据链行写作，不必通读全文 |
| 任一脚本异常 | 读 stderr；能修则修后重跑（幂等）；不能则保留已有产物 status=partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `proposal_draft.md` | 清洁章节稿：七要素齐全，可直接粘贴进申请书 |
| `proposal_annotated.md` | 留痕版：段首 D-Pxxx，〔F〕〔拟〕〔确认〕原位保留 |
| `element_mapping.md` | 要素对照说明：七要素×章节×厚度×证据数×状态 + 三级对应清单 |
| `evidence_chain.json`（work 下） | 审定版证据链：能力—证据 FID—来源—与本研究关系（可复用资产） |
| `evidence_chain_seed.json`（work 下） | 机选初稿（审定对照用，不交付） |
| `report.md` | 质量报告：覆盖表、发现分级统计、来源核验统计、异常限制 |
| `preview.html`（+`preview.pdf` 尽力） | 交付预览 |
| `result.json` | 契约结果：case_id、status、outputs、evidence_map、change_log、uncertainty、output_contract 回填 |

## 关键方法（详见 references/）

- `references/feasibility_method.md`：证据链三列判据、已完成/拟开展体貌词表与判例、成果断言锚定规则、误报来源。
- `references/failure_modes.md`：基础 Agent 在研究基础节上的典型失败模式与本技能对策。
- `references/worked_example.md`：完整标注示例（合成案例，非正式测试案例）。

## 限制

- 证据链行基于角色与信号词启发式机选，低频/隐式的前期基础表述可能漏选；Agent 可在第 6 步手工增行。
- 体貌机检基于信号词表（已/了/发表/获得/建立 vs 拟/将/计划/预期），不能判断语义真伪——
  "锚定的 FID 是否真正支撑该成果断言"由第 12 步 Agent 复核保证。
- 关系列（relation_to_project）的填写质量完全由 Agent 决定，机检只能发现"空缺"，不能判断"牵强"。
