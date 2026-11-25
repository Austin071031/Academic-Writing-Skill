---
name: grant-innovation-precision
description: 基金申请书写作技能（主攻"说得准：创新点写清与具体已有工作的差别，不依赖首次/国际领先/填补空白一类无法核验的修饰"）。基于案例材料（原论文、前期成果、组织方 workorder）撰写覆盖七要素的申请书章节稿，创新点节按"差异定位三段式"组织：脚本先从材料机选代表性已有工作对比锚点与 gap 上下文（innovation_seed.json），Agent 审定后逐条按"锚定已有工作→差异表述→凭什么成"落稿，机检审计不可核验修饰词（high）、无对比锚点、无差异表述、三维覆盖缺环，全部定位到草稿段并给出替换指令。事实台账（fact_ledger）+ 证据标记语法（〔F0001〕〔拟〕〔确认〕）保证每个数字/引用可回溯、材料外事实零容忍、已完成与拟开展分清。适用于国家自然科学基金等中文申请书核心章节（立项依据/科学问题/研究目标/研究内容/创新点/技术路线/研究基础）的起草与创新点体检；不适用于无科研材料输入的空写场景（如实降级 partial）。本版（v2.0.4）新增增益自评卡：反事实缺陷对照（若无本技能机检哪些缺陷将留在稿中）+ 修订闭环统计 + 机械劳动量化，自动嵌入 report.md 末尾，增益证据显式可核验。输入 /input 下 case.json、task.md、organizer-workorder.json 与材料文件，输出 /app/output 下 proposal_draft.md（清洁章节稿）、proposal_annotated.md（留痕版）、element_mapping.md（七要素对照说明）、innovation_seed.json、gain_card.md（增益自评卡）、report.md、result.json。
---

# 创新点差异定位 · 基金申请书写作 Skill

## 用途与适用条件

对组织方给定科研案例撰写**可直接进入申请书的章节稿＋要素对照说明**，主攻题面"说得准"：
创新点不是"首次/国际领先/填补空白"式表态的堆叠，而是逐条可复核的差异定位——
**锚定已有工作（谁做到了什么，带〔F〕锚点）→ 差异表述（本课题不同于/区别于/而非什么）→ 凭什么成（申请人已完成的前期基础）**，
并保证全节覆盖"新在哪里 / 为什么难 / 凭什么做得成"三个维度。
机制：脚本承担全部机械劳动（材料解析、事实台账、对比锚点机选、修饰词/锚点/差异/三维机检、
要素覆盖检查、材料外事实审计、契约组装），Agent 只做三件事——**审定锚点候选、撰写带证据标记的章节稿、处置机检发现**。

适用：有原论文/前期成果/指南类材料的中文基金申请书章节起草与创新点节体检。
不适用：无任何材料输入（按材料缺口如实降级，登记 manual_confirmations）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、可能存在的 `/input/organizer-workorder.json` 与材料文件（md/txt/tex/docx/pdf）；工作目录 `/app/work`；交付目录 `/app/output`。
- 预算：64 次模型请求 / 900 秒。**章节稿按要素逐个落盘（work/sections/），脚本随时可组装部分结果，防超时空手**。
- 本目录即技能根：`scripts/`（管线 14 个脚本）、`references/`（方法判据 method_rules.md + 标注示例 worked_example.md）、`examples/minimal_example.md`。

## 三条红线（违反即失去正确性分）

1. **不臆造事实**：数字、引用、前期成果、术语只能来自 fact_ledger.json 台账（写作时用〔F0001〕标记锚定）；台账没有的事实禁止写入章节稿。拟开展内容/预期指标必须标〔拟〕；材料不足/冲突标〔确认〕并登记 manual_confirmations。
2. **不伪造核验**：机检发现（findings）逐条复核处置，成立的修订、误报的驳回并写明理由；不得删除 findings 文件充清零。
3. **不用不可核验修饰**：创新点节（乃至全稿）禁用 首次/国际领先/填补空白/国际先进/国内首创/世界领先/原创性/重大突破/国际一流/领跑；创新表述只能写成"与具体已有工作的差异 + 〔F〕锚点 + 可核验指标/机制差异"。

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

# 5) 创新点对比锚点机选：代表性已有工作锚点 + gap 上下文
python3 $S/innovation_engine.py seed --work $W
cat $W/innovation_seed.json
```

**第 6 步（Agent 核心判断①：通读与审定）**。
读 `work/materials_digest.md`（全文 pid 标注摘要）与 `work/innovation_seed.json`：
- 复核 parse_materials 的 role_guess 是否准确（启发式可能误判，误判则心里更正后按正确角色取用事实）；
- 从 prior_work_anchors 中选定每条创新点要对比的代表性已有工作（每条创新点至少 1 个锚点），
  从 gap_contexts 归纳该差异要攻克的难点；锚点空缺（如 paper 角色材料缺失）登记
  `work/manual_confirmations.json`。

**第 7 步（Agent 核心判断②：分节撰写章节稿）**。按 inspection.json 的 required_elements 逐节写
`work/sections/NN_要素名.md`（NN=01..07；首行 `# 要素名`，如 `# 创新点`）：
- **证据标记语法（强制）**：材料事实句末标 `〔F0001〕`（FID 必须存在于 fact_ledger.json）；
  拟开展/预期内容标 `〔拟〕`；需人工确认标 `〔确认〕`。
- **创新点节（本技能主攻）**：逐条按差异定位三段式写——
  ①锚定已有工作：从 innovation_seed.json 选具体已有工作并带〔F〕（或写明 已有工作/现有研究/文献）；
  ②差异表述：用 不同于/区别于/相比/优于/而非/改为 写清做法差异，优势只写可核验的机制或指标差异；
  ③三维落笔：全节合起来必须覆盖 新在哪里（提出/引入/建立/发展 + 新机制/新方法）、
  为什么难（难点/挑战/瓶颈/耦合复杂）、凭什么做得成（申请人/本团队/前期/平台/基础，带〔F〕）。
  禁用黑名单修饰词；不写"首次提出"，改写为"提出…，不同于已有工作 X〔F〕"。
- 其余六节：立项依据按 现状→瓶颈→我们 组织并逐条锚定；科学问题承接瓶颈；
  研究目标/研究内容/技术路线/考核指标逐条对应；研究基础区分已完成/拟开展。
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

# 11) 创新点专项审计：修饰词黑名单/无对比锚点/无差异表述/三维缺环
python3 $S/innovation_engine.py audit --work $W
cat $W/findings.json
```

**第 12 步（Agent 复核与修订，禁止跳过）**：
1. **删误报**：对照 materials.json 原文复核 source_audit.json、element_findings.json、findings.json
   每条发现；确属误报的在对应文件将该条加 `"status":"已驳回"` 并写理由。
2. **修订**：成立的发现逐条修订 sections 文件（修饰词改差异句式、补对比锚点〔F〕、
   补差异表述、补齐缺失维度），把每处修改追加到 `work/change_log.json`
   （{"op","location","before","after","reason"}），然后重跑第 8-11 步确认 high 级清零。
3. **标注边界**：材料外但任务必需的常识性内容，标〔拟〕或〔确认〕并在 uncertainty 说明。

```bash
# 13) 增益自评卡（report 前必跑）+ 报告 + 契约组装 + 发布闸门 + 预览
python3 $S/gain_card.py --work $W --out $O    # 生成 O/gain_card.md，report_builder 自动嵌入 report.md 末尾
python3 $S/report_builder.py --work $W --out $O \
    --focus innovation --skill "grant-innovation-precision v1.0.3"
python3 $S/assemble_result.py --work $W --out $O \
    --skill "grant-innovation-precision v1.0.3" --status success   # 有未处置 high/缺材料用 partial
python3 $S/validate_output.py --out $O --work $W    # 必须 PASS
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理（识别并如实记录，不得静默）

| 情况 | 处置 |
|-|-|
| 无材料文件 / 空文件 | 保留骨架，status=failed，exceptions 记录原因 |
| PDF 无 pdftotext 或抽取为空 | exceptions 记录；该文件事实缺失，status≤partial |
| role_guess 误判（指南被判成 paper 等） | Agent 按真实角色取用锚点；在 uncertainty 注明复核结论 |
| 锚点候选为空（paper 角色材料缺失） | 创新点对比对象改用文献综述式表述并登记 manual_confirmations，status=partial |
| 创新点节用别名（特色与创新/创新与特色） | 引擎自动兼容；sections 文件名与首行标题保持一致即可 |
| workorder 与 task.md 要求冲突 | 以 organizer-workorder.json 为准，冲突写入 uncertainty |
| FID 标记指向不存在条目 | draft_builder 报 findings_draft（high）；修正标记后重跑 |
| 超长材料（段落>800） | digest 已截断；优先按锚点候选写作，不必通读全文 |
| 任一脚本异常 | 读 stderr；能修则修后重跑（幂等）；不能则保留已有产物 status=partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `proposal_draft.md` | 清洁章节稿：七要素齐全，可直接粘贴进申请书 |
| `proposal_annotated.md` | 留痕版：段首 D-Pxxx，〔F〕〔拟〕〔确认〕原位保留 |
| `element_mapping.md` | 要素对照说明：七要素×章节×厚度×证据数×状态 + 三级对应清单 |
| `innovation_seed.json` | 创新点对比锚点与 gap 上下文候选（可复用资产） |
| `gain_card.md` | 增益自评卡：反事实缺陷对照 + 修订闭环 + 机械劳动量化（report_builder 自动嵌入 report.md 末尾） |
| `report.md` | 质量报告：覆盖表、发现分级统计、来源核验统计、异常限制、增益自评卡节 |
| `preview.html`（+`preview.pdf` 尽力） | 交付预览 |
| `result.json` | 契约结果：case_id、status、outputs、evidence_map、change_log、uncertainty、output_contract 回填 |

## 关键方法（详见 references/）

- `references/method_rules.md`：差异定位三段式、修饰词黑名单与替换句式库、三维判据、误报来源、基础 Agent 典型失败模式与对策（原 innovation_method.md 与 failure_modes.md 合并）。
- `references/worked_example.md`：完整标注示例（合成案例，非正式测试案例）。

## 限制

- 锚点候选基于角色启发式与事实类型过滤，paper 角色材料中的非引用类已有工作线索可能漏选；Agent 可在第 6 步手工补充。
- 机检只能核对"条目是否有对比锚点与差异词"，不能判断差异表述在科学上是否成立——语义正确性由第 12 步 Agent 复核保证。
- 三维判据按全节关键词覆盖检查，属必要而非充分条件；条目切分基于编号/段落启发式，跨段合写的条目按段判定。
- 修饰词黑名单覆盖常见表述，学科特有套话靠 declared 词表扩展（references/method_rules.md）。
