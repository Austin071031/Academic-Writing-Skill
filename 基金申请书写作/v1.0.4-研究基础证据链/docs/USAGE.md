# 使用说明（grant-feasibility-evidence v1.0.4）

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
`fact_ledger.json`、`fact_ledger.md`、`evidence_chain_seed.json`、`evidence_chain.json`（Agent 审定版）、
`draft.json`、`source_audit.json`、`element_map.json`、`findings.json` 等。

## 调用步骤

严格按 `SKILL.md` 标准工作流 13 步执行。Agent 的三处核心判断：

1. **第 6 步 审定证据链**：读 `materials_digest.md` + `evidence_chain_seed.json`，
   取舍机选行、核对 capability 与 evidence_fids、逐行填写 relation_to_project，
   另存 `work/evidence_chain.json`；复核 role_guess；缺口登记 manual_confirmations。
2. **第 7 步 分节写作**：`work/sections/NN_要素名.md`，强制证据标记〔F0001〕〔拟〕〔确认〕；
   研究基础节按证据链组织，成果断言逐条带〔F〕、拟开展逐处带〔拟〕且体貌不混。
3. **第 12 步 复核修订**：处置 source_audit / element_findings / findings 三个文件中的每条发现，
   修订后重跑第 8-11 步至 high 级清零。

## 证据标记语法

| 标记 | 含义 | 机检行为 |
|-|-|-|
| `〔F0001〕` | 该句事实来自台账条目 F0001 | FID 必须存在；数字/引用与台账值比对；研究基础节中成果断言无此标记 → high |
| `〔拟〕` | 拟开展/预期内容 | 段内数字不做材料外审计；体貌必须为拟态，判为 completed → high |
| `〔确认〕` | 材料不足/冲突，需人工确认 | 登记 manual_confirmations 后放行 |

## 体貌规则速查（audit 规则 2/3）

- 段落带〔拟〕，剥掉标记后体貌判 **completed**（含 已/了/发表/获得/建立 等）→
  `aspect_violation_planned_as_done`（high）：拟开展内容写成了已完成体。
- 段落锚定成果类〔F〕（台账 type=pub_mention/number 且来源 prior_work 文件），体貌判 **planned**
  （含 拟/将/计划/预期）→ `aspect_violation_done_as_planned`（medium）：已完成成果写成了拟开展体。
- 段落同时含两类信号判 mixed，不命中上述规则——但建议拆段，一段一体貌。

## 自查方法

- `validate_output.py` 必须 PASS（8 项形态检查）。
- `report.md` 的 findings 分级统计中 high 必须为 0（或全部"已驳回"并附理由）。
- `element_mapping.md` 七要素状态应为 ok（thin/missing 需在 report 说明原因）。
- `work/evidence_chain.json` 存在且每行 relation_to_project 非空。
- 抽查 `proposal_annotated.md` 研究基础节 3 处〔F〕标记，对照 `fact_ledger.md` 验证来源属实。

## 适用场景与限制

见 `SKILL.md` 用途与限制节。核心限制：机检查"有没有锚点、体貌是否自洽"，
语义支撑与关系列质量由 Agent 复核保证；role_guess 为启发式，Agent 须在第 6 步复核。

## 失败处理

任一脚本失败：读 stderr → 修复后重跑（全部幂等）→ 无法修复则保留已有产物，
`assemble_result.py --status partial` 交付并在 report.md 写明限制。
