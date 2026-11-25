# 使用与方法说明（section-narrative-flow v2.0.3）

## 调用步骤

1. **环境**：Python ≥ 3.8（纯标准库）；如需解析 PDF，系统需有 `pdftotext`（缺失时按异常表降级，不影响其他格式）。
2. **输入**：`/input/case.json`（含 case_id 与 output_contract）、`/input/task.md`、稿件文件（md/txt/tex/docx/pdf）。多稿件时 `parse_manuscript.py --file <路径>` 指定。
3. **运行**：按 SKILL.md「标准工作流」8 步执行；脚本幂等，中断后重跑继续。第 6 步后运行 `gain_card.py --work /app/work --out /app/output` 生成增益自证卡；第 7 步若增删 findings 须重跑一次以刷新指标（幂等）。
4. **判断**：第 7 步必须人工/Agent 复核草稿——脚本产出候选，误报删除、漏报补登（须带原文锚点）、优先级重排。
5. **交付**：`validate_output.py` 返回 PASS 方可视为完成；status 必须诚实（success/partial/failed）。

## 输入输出解释

| 产物 | 说明 |
|-|-|
| diagnosis_report.md | 主交付。六维分节；每条问题：ID / 维度 / 类型 / 位置（章节›段落›句子）/ 原文锚点 / 判断依据 / 编辑动作 / 严重度 / 置信度 / 复核状态 |
| edit_plan.json | 机读编辑计划；`ops[]` 与 findings 同 ID，作者逐条执行并勾选采纳/部分采纳/驳回 |
| findings.json | 全部问题的统一 schema，便于二次开发 |
| section_map.json | 主攻维度中间产物：角色序列表（含逆序对）、篇幅占比表、缩写首现表 |
| restructured_outline.md | 重组大纲草稿：现状序列 → 建议叙事顺序（各节去向 + 动作汇总） |
| gain_card.md / gain_card.json | 增益自证卡（v2.0.3 新增）：机器可复算的增益指标 + 与基础 Agent 的反事实对照表 |
| result.json | 平台契约：case_id + output_contract 全部字段 + status/outputs/evidence_map/change_log/uncertainty/stats |

### 增益自证卡指标与复算口径（gain_card.py）

- **六维覆盖率**（x/6）：findings.json 按 dimension 计数；无 finding 的维度，diagnosis_report.md 该维度节内含显式"未检出"说明即计为覆盖。
- **原文锚点率**：quote 非空且不以"(未检出"/"(全文)"占位开头的 finding 占比。
- **可执行动作率**：action.op ∈ 9 类允许 op（move/merge/split/narrow/qualify/add/add_transition/add_limitation/reorder）且 instruction 非空的占比。
- **定位粒度分布**：location.sentence_id 非空=句子级；仅 para_id=段落级；皆空=全文级。
- **机械劳动清单**：work/change_log.json 中步骤名属脚本管线（inspect/parse/six_scan/section_flow 等）的条目数；其余条目记为 Agent 判断步骤。
- **估计效率**：人工逐条通读基线 = n_chars ÷ 1500 字/分钟（估计）；脚本管线 = 步骤数 × 秒级（估计）。两栏均为量级估计，表内已注明，不作精确承诺。
- **反事实对照表**：左列"基础 Agent 典型输出"为固定文案示例（反事实示意，非实测）；右列为 findings.json 中 high severity 前 5 条的 位置｜类型｜op 摘录。
- 复算方法：重跑 `gain_card.py` 或按上述口径直接对 findings.json / work/stats.json / work/change_log.json 计数；同一数字同时写入 gain_card.md、gain_card.json 与 diagnosis_report.md 末尾"## 增益自证卡（机器可复算）"节。

## 关键方法

- **结构解析**（parse_manuscript.py）：行级标题识别（Markdown `#`、LaTeX `\section`、纯文本的数字编号/中文编号/关键词标题、docx 样式、PDF 文本层），段落空行切分，句子按中英终结符切分，发稳定 ID。
- **六维普查**（six_scan.py）：每维度 ≤8 条候选，保证"结果完整性"评分要求的六类覆盖；未检出维度在报告中显式说明。
- **章节流引擎**（section_flow.py）：
  - 角色归类：标题关键词 → 12 类角色（`ROLE_MAP`）；正文占比 = 章节字符 / 非后置章节总字符。
  - 逆序对：角色序列表与 `CANONICAL_ORDER`（摘要→…→参考文献→附录）两两比对，后者规范序低于前者即一条 move 候选。
  - 篇幅阈值：`THRESH.section_imbalance=0.55`（拆分）、方法 <8% 且存在结果章（方法过薄）、引言 >35%（铺垫过长）。
  - 层级与空章：相邻标题层级差 >1（跳变）、同级同名标题（合并候选）、n_para=0（空章）。
  - 缩写首现：正则 `[A-Z][A-Z0-9]{1,7}s?` 抽取；在首现句及相邻句查"全称（ABBR）/ ABBR（全称）"定义模式，未命中即"信息过早释放"。
  - 回指悬空："如前所述/aforementioned"句与前 200 词内容词重叠 ≈0 → add_transition 候选。
  - 方法泄漏：结果/讨论/结论章段落含 ≥2 句方法性描述（采用/步骤/配置为…）→ 后移方法章候选。

## 适用场景与限制

- 适用：IMRaD 类中英文稿件的投稿前结构自查、导师初审、同行评审前自检、章节重组编辑。
- 限制：词面/标题关键词方法对同义改写与刁钻标题不敏感；非标准文体（综述、观点文）序列判定置信度下降。所有阈值见 `scripts/scanutil.py:THRESH`。

## 失败处理与自查

- 任一步失败：先读 stderr 的 `[脚本名][issue]` 行；脚本均可独立重跑。
- 交付前自查（对应 evaluation/scoring_sheet.md）：①每条问题能否按位置+锚点指回原文？②六维是否都有结论（含"未检出"说明）？③status 是否与 uncertainty/exceptions 一致？④result.json 是否含 case_id 与全部契约字段？⑤section_map.json 与 restructured_outline.md 是否生成且与报告一致？
