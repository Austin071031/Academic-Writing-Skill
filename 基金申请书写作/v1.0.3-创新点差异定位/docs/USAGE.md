# 使用说明（grant-innovation-precision v1.0.3）

## 输入

| 路径 | 说明 |
|-|-|
| `/input/case.json` | 案例元数据（case_id、output_contract 等） |
| `/input/task.md` | 写作任务要求 |
| `/input/organizer-workorder.json` | 组织方补充约束（可选；存在时优先级最高） |
| `/input/*.{md,txt,tex,docx,pdf}` | 科研材料：原论文、前期成果、指南等（格式不限） |

## 输出（/app/output）

`proposal_draft.md`（清洁章节稿）、`proposal_annotated.md`（留痕版）、
`element_mapping.md`（七要素对照说明）、`report.md`、`preview.html`、`result.json`。
中间产物（/app/work）：`inspection.json`、`materials.json`、`materials_digest.md`、
`fact_ledger.json`、`fact_ledger.md`、`innovation_seed.json`、`draft.json`、
`source_audit.json`、`element_map.json`、`findings.json` 等。

## 调用步骤

严格按 `SKILL.md` 标准工作流 13 步执行。Agent 的三处核心判断：

1. **第 6 步 审定锚点**：读 `materials_digest.md` + `innovation_seed.json`，
   为每条规划中的创新点选定 ≥1 个代表性已有工作锚点（prior_work_anchors），
   从 gap_contexts 归纳难点；复核 role_guess；缺口登记 manual_confirmations。
2. **第 7 步 分节写作**：`work/sections/NN_要素名.md`，强制证据标记〔F0001〕〔拟〕〔确认〕；
   创新点节逐条按 锚定已有工作→差异表述→三维落笔 组织，禁用黑名单修饰词。
3. **第 12 步 复核修订**：处置 source_audit / element_findings / findings 三个文件中的每条发现，
   修订后重跑第 8-11 步至 high 级清零。

## 证据标记语法

| 标记 | 含义 | 机检行为 |
|-|-|-|
| `〔F0001〕` | 该句事实来自台账条目 F0001 | FID 必须存在；数字/引用与台账值比对；创新点节中指向 citation/pub_mention 类的标记兼作对比锚点 |
| `〔拟〕` | 拟开展/预期内容 | 段内数字不做材料外审计；体貌须为拟态 |
| `〔确认〕` | 材料不足/冲突，需人工确认 | 登记 manual_confirmations 后放行 |

## 创新点节判定规则速查（innovation_engine.py audit）

| kind | severity | 触发条件 | 处置 |
|-|-|-|-|
| missing_section | high | 草稿无 创新点/特色与创新/创新与特色 节 | 补写该节 |
| banned_modifier | high | 命中 首次/国际领先/填补空白/国际先进/国内首创/世界领先/原创性/重大突破/国际一流/领跑 | 删除命中词，改为差异表述 + 〔F〕锚点 |
| no_baseline_anchor | medium | 条目无 citation/pub_mention 类〔F〕且无 已有工作/现有研究/现有方法/文献/传统方法/目前主流 | 从 innovation_seed.json 选锚点补对比对象 |
| no_difference_statement | medium | 条目无 不同于/区别于/相比/优于/而非/改为/突破了/克服了/解决了/避免了 | 补差异句 |
| three_dim_incomplete | medium | 全节缺 新在哪里/为什么难/凭什么做得成 任一维（「首次提出」不算新维度证据） | 按 msg 指明的缺维补写 |

## 自查方法

- `validate_output.py` 必须 PASS（8 项形态检查）。
- `report.md` 的 findings 分级统计中 high 必须为 0（或全部"已驳回"并附理由）。
- `element_mapping.md` 七要素状态应为 ok（thin/missing 需在 report 说明原因）。
- 抽查 `proposal_annotated.md` 创新点节每条：能否指出对比的已有工作及其〔F〕锚点、
  差异表述词、以及该条归属的三维覆盖。

## 适用场景与限制

见 `SKILL.md` 用途与限制节。核心限制：机检查"有没有锚点与差异词"，语义支撑由 Agent 复核保证；
role_guess 为启发式，Agent 须在第 6 步复核；条目切分基于编号/段落启发式。

## 失败处理

任一脚本失败：读 stderr → 修复后重跑（全部幂等）→ 无法修复则保留已有产物，
`assemble_result.py --status partial` 交付并在 report.md 写明限制。
