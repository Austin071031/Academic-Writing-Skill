---
name: grant-innovation-precision
description: 基金申请书写作技能（主攻"说得准：创新点写清与具体已有工作的差别，不依赖首次/国际领先/填补空白一类无法核验的修饰"）。基于案例材料（原论文、前期成果、组织方 workorder）撰写覆盖七要素的申请书章节稿，创新点节按"差异定位三段式"组织：脚本先从材料机选代表性已有工作对比锚点与 gap 上下文（innovation_seed.json），Agent 审定后逐条按"锚定已有工作→差异表述→凭什么成"落稿，机检审计不可核验修饰词（high）、无对比锚点、无差异表述、三维覆盖缺环，全部定位到草稿段并给出替换指令。事实台账（fact_ledger）+ 证据标记语法（〔F0001〕〔拟〕〔确认〕）保证每个数字/引用可回溯、材料外事实零容忍、已完成与拟开展分清。本版单点改动：快速主通道——sections_scaffold 骨架预生成 + 分阶段请求预算表，工作流压缩为 8 步，保证 900 秒预算内完整七节成稿。不适用于无科研材料输入的空写场景（如实降级 partial）。输入 /input 下 case.json、task.md、organizer-workorder.json 与材料文件，输出 /app/output 下 proposal_draft.md（清洁章节稿）、proposal_annotated.md（留痕版）、element_mapping.md（七要素对照说明）、innovation_seed.json、report.md、result.json。
---

# 创新点差异定位 · 基金申请书写作 Skill（v2.0.0 快速主通道）

## 分阶段请求预算表（总预算 ≤40 请求 / 900 秒，主通道 8 步）

| Phase | 命令 | Agent 动作 | 请求预算 | 断点续跑约定 |
|-|-|-|-|-|
| 1 兜底骨架 | init_result.py | 无 | 1 | 幂等，可随时重跑 |
| 2 案例侦察 | inspect_case.py | 读 inspection.json | 2 | 幂等；重跑覆盖 inspection.json |
| 3 材料解析 | parse_materials.py | 无 | 1 | 幂等；digest 供 Phase 6 通读 |
| 4 事实台账 | fact_ledger.py | 无 | 1 | 幂等；FID 全稿唯一事实来源 |
| 5 骨架+锚点 | sections_scaffold.py + innovation_engine.py seed | 扫读骨架候选清单 | 2 | 骨架幂等：含〔F〕的文件不覆盖 |
| 6 成稿（核心） | —（Agent 写作） | 读 materials_digest.md + innovation_seed.json，一轮写完七节 | 18 | 逐节落盘 work/sections/，随时可组装部分结果 |
| 7 组装+四审计 | draft_builder.py + source_audit.py + elements_check.py + innovation_engine.py audit | 读 4 个 findings，处置 high | 8 | 修订后整 Phase 重跑一轮即可 |
| 8 交付 | report_builder.py + assemble_result.py + validate_output.py + render_previews.py | 读 report.md 核对 | 5 | validate 必须 PASS 才算完成 |
| 机动 | — | 第二轮复核修订（仅剩余预算>15 才做） | 2 | 预算耗尽 → 跳交付 partial 并如实标注 |
| **合计** | | | **≤40** | |

断点续跑总约定：全部脚本幂等；任何中断后按上表从最近完成 Phase 的下一 Phase
续跑即可，已写 sections 不会被 scaffold 覆盖（含〔F〕即视为成稿）。

## 用途与适用条件

对组织方给定科研案例撰写**可直接进入申请书的章节稿＋要素对照说明**，主攻题面"说得准"：
创新点不是"首次/国际领先/填补空白"式表态的堆叠，而是逐条可复核的差异定位——
**锚定已有工作（谁做到了什么，带〔F〕锚点）→ 差异表述（本课题不同于/区别于/而非什么）→ 凭什么成（申请人已完成的前期基础）**，
并保证全节覆盖"新在哪里 / 为什么难 / 凭什么做得成"三个维度。
机制：脚本承担全部机械劳动（材料解析、事实台账、**骨架与候选事实预生成**、对比锚点机选、
修饰词/锚点/差异/三维机检、要素覆盖检查、材料外事实审计、契约组装），
Agent 只做两件事——**在骨架上一轮写完七节成稿、处置机检发现**。

适用：有原论文/前期成果/指南类材料的中文基金申请书章节起草与创新点节体检。
不适用：无任何材料输入（按材料缺口如实降级，登记 manual_confirmations）。

## 运行契约（平台环境）

- 输入：`/input/case.json`、`/input/task.md`、可能存在的 `/input/organizer-workorder.json` 与材料文件（md/txt/tex/docx/pdf）；工作目录 `/app/work`；交付目录 `/app/output`。
- 预算：64 次模型请求 / 900 秒；本技能按上表把主通道压到 ≤40 请求，余量全部留给写作厚度。**章节稿在骨架上直接成稿、逐节落盘（work/sections/），脚本随时可组装部分结果，防超时空手**。
- 本目录即技能根：`scripts/`（管线 14 个脚本）、`references/`（方法判据）、`examples/minimal_example.md`。

## 三条红线（违反即失去正确性分）

1. **不臆造事实**：数字、引用、前期成果、术语只能来自 fact_ledger.json 台账（写作时用〔F0001〕标记锚定；骨架注释里的候选清单就是首选取材池）；台账没有的事实禁止写入章节稿。拟开展内容/预期指标必须标〔拟〕；材料不足/冲突标〔确认〕并登记 manual_confirmations。
2. **不伪造核验**：机检发现（findings）逐条复核处置，成立的修订、误报的驳回并写明理由；不得删除 findings 文件充清零。
3. **不用不可核验修饰**：创新点节（乃至全稿）禁用 首次/国际领先/填补空白/国际先进/国内首创/世界领先/原创性/重大突破/国际一流/领跑；创新表述只能写成"与具体已有工作的差异 + 〔F〕锚点 + 可核验指标/机制差异"。

## 标准工作流（8 步主通道，严格按序执行）

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

# 5) 骨架预生成 + 创新点对比锚点机选（一条命令组，两个脚本）
python3 $S/sections_scaffold.py --work $W      # 生成 work/sections/01..07 骨架（含 FID 候选清单）
python3 $S/innovation_engine.py seed --work $W
cat $W/innovation_seed.json
```

**第 6 步（Agent 核心写作：读摘要与候选，一轮写完七节）**。
读 `work/materials_digest.md`（全文 pid 标注摘要）、`work/innovation_seed.json`，
并浏览 `work/sections/` 七个骨架注释中的候选事实清单：
- 复核 parse_materials 的 role_guess 是否准确（启发式可能误判，误判则心里更正后按正确角色取用事实）；
- 从 prior_work_anchors 中选定每条创新点要对比的代表性已有工作（每条创新点至少 1 个锚点），
  从 gap_contexts 归纳该差异要攻克的难点；锚点空缺登记 `work/manual_confirmations.json`；
- **直接在骨架文件上成稿**（覆写 `work/sections/NN_要素名.md`，NN=01..07；首行保持
  `# 要素名`），一轮连续写完七节，不中途回头：
  - **证据标记语法（强制）**：材料事实句末标 `〔F0001〕`（FID 必须存在于
    fact_ledger.json，骨架候选清单已按要素预筛 ≤12 条，优先从中取材）；
    拟开展/预期内容标 `〔拟〕`；需人工确认标 `〔确认〕`。
  - **创新点节（本技能主攻）**：逐条按差异定位三段式写——
    ①锚定已有工作：从 innovation_seed.json 选具体已有工作并带〔F〕（或写明 已有工作/现有研究/文献）；
    ②差异表述：用 不同于/区别于/相比/优于/而非/改为 写清做法差异，优势只写可核验的机制或指标差异；
    ③三维落笔：全节合起来必须覆盖 新在哪里（提出/引入/建立/发展 + 新机制/新方法）、
    为什么难（难点/挑战/瓶颈/耦合复杂）、凭什么做得成（申请人/本团队/前期/平台/基础，带〔F〕）。
    禁用黑名单修饰词；不写"首次提出"，改写为"提出…，不同于已有工作 X〔F〕"。
  - 其余六节：立项依据按 现状→瓶颈→我们 组织并逐条锚定；科学问题承接瓶颈；
    研究目标/研究内容/技术路线/考核指标逐条对应；研究基础区分已完成/拟开展。
  - 厚度：按骨架标注的字数目标写足（立项依据≥600 字、技术路线≥450 字、
    研究基础与可行性≥400 字、其余≥250 字；若 inspection.deliverable_hints 或
    workorder 另有更高要求从其高者）。
  - **预算兜底**：按预算表监控请求数；Phase 6 预算（18 请求）耗尽仍未写完，
    立即跳到第 8 步交付 partial，已写节照样组装。

```bash
# 7) 组装 + 四审计一轮跑完（清洁版/留痕版/要素对照 + FID 校验 + 材料外事实 +
#    厚度覆盖 + 创新点专项）
python3 $S/draft_builder.py --work $W --out $O
python3 $S/source_audit.py --work $W
python3 $S/elements_check.py --work $W --out $O
python3 $S/innovation_engine.py audit --work $W
cat $W/source_audit.json $W/element_findings.json $W/findings_draft.json $W/findings.json
```

读完四个 findings 文件后**当轮处置全部 high 级发现**：成立的直接改 sections，
误报的在该文件加 `"status":"已驳回"` 并写理由；修订记入 `work/change_log.json`
（{"op","location","before","after","reason"}）。修订后把第 7 步整体重跑一轮
（四脚本均幂等），确认 high 级清零即进入第 8 步。
**第二轮复核修订环降级为可选**：仅当按预算表估算剩余预算 >15 请求时才做
（对 medium/low 级发现做一轮精修并重跑第 7 步）；否则直接交付。

```bash
# 8) 报告 + 契约组装 + 发布闸门 + 预览
python3 $S/report_builder.py --work $W --out $O \
    --focus innovation --skill "grant-innovation-precision v2.0.0"
python3 $S/assemble_result.py --work $W --out $O \
    --skill "grant-innovation-precision v2.0.0" --status success   # 有未处置 high/缺材料用 partial
python3 $S/validate_output.py --out $O --work $W    # 必须 PASS
python3 $S/render_previews.py --out $O --work $W
```

## 异常处理（识别并如实记录，不得静默）

| 情况 | 处置 |
|-|-|
| 无材料文件 / 空文件 | 保留骨架，status=failed，exceptions 记录原因 |
| PDF 无 pdftotext 或抽取为空 | exceptions 记录；该文件事实缺失，status≤partial |
| role_guess 误判（指南被判成 paper 等） | Agent 按真实角色取用锚点；在 uncertainty 注明复核结论 |
| 骨架候选清单为空（台账为空或要素无匹配） | 先确认 fact_ledger 已跑；仍为空则按 digest 写作并登记 manual_confirmations |
| scaffold 重跑覆盖了未带〔F〕的半成稿 | 设计如此（无〔F〕视为骨架）；半成稿至少先落一条〔F〕再中断，或从候选清单快速补标 |
| 锚点候选为空（paper 角色材料缺失） | 创新点对比对象改用文献综述式表述并登记 manual_confirmations，status=partial |
| 创新点节用别名（特色与创新/创新与特色） | 引擎自动兼容；sections 文件名与首行标题保持一致即可 |
| workorder 与 task.md 要求冲突 | 以 organizer-workorder.json 为准，冲突写入 uncertainty |
| FID 标记指向不存在条目 | draft_builder 报 findings_draft（high）；修正标记后重跑 |
| 超长材料（段落>800） | digest 已截断；优先按骨架候选清单与锚点候选写作，不必通读全文 |
| 任一脚本异常 | 读 stderr；能修则修后重跑（幂等）；不能则保留已有产物 status=partial |

## 输出物清单

| 文件 | 内容 |
|-|-|
| `proposal_draft.md` | 清洁章节稿：七要素齐全，可直接粘贴进申请书 |
| `proposal_annotated.md` | 留痕版：段首 D-Pxxx，〔F〕〔拟〕〔确认〕原位保留 |
| `element_mapping.md` | 要素对照说明：七要素×章节×厚度×证据数×状态 + 三级对应清单 |
| `innovation_seed.json` | 创新点对比锚点与 gap 上下文候选（可复用资产） |
| `report.md` | 质量报告：覆盖表、发现分级统计、来源核验统计、异常限制 |
| `preview.html`（+`preview.pdf` 尽力） | 交付预览 |
| `result.json` | 契约结果：case_id、status、outputs、evidence_map、change_log、uncertainty、output_contract 回填 |

## 关键方法（详见 references/）

- `references/method_rules.md`：差异定位三段式、修饰词黑名单与替换句式库、三维判据、
  基础 Agent 典型失败模式与对策、scaffold 匹配规则。
- `references/worked_example.md`：完整标注示例（合成案例，非正式测试案例）。

## 限制

- 骨架候选清单按要素关键词与 role_guess 启发式匹配，属"首选取材池"而非全集；
  Agent 可在第 6 步从 materials_digest.md 补充候选外 FID。
- 锚点候选基于角色启发式与事实类型过滤，paper 角色材料中的非引用类已有工作线索可能漏选；Agent 可在第 6 步手工补充。
- 机检只能核对"条目是否有对比锚点与差异词"，不能判断差异表述在科学上是否成立——语义正确性由第 7 步 Agent 复核保证。
- 三维判据按全节关键词覆盖检查，属必要而非充分条件；条目切分基于编号/段落启发式，跨段合写的条目按段判定。
- 修饰词黑名单覆盖常见表述，学科特有套话靠 declared 词表扩展（references/method_rules.md 附录）。
- 骨架字数目标（600/450/400/250）是写作厚度引导；elements_check 机检阈值
  （400/300/150）未改，二者不一致时以任务要求为准写足厚度。
