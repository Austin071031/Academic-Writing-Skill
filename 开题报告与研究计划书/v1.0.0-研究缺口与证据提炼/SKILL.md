---
name: proposal-gap-evidence
description: 从课题指南、前期数据与文献中提炼“已知—未知—待验证”研究缺口并生成全要素开题报告。当任务要求依据给定科研材料撰写或修改开题报告、研究计划书、课题论证（尤其是背景与立项依据部分）时使用。以证据清单驱动的缺口陈述保证每条背景论断可回溯，避免文献罗列；输出含证据矩阵的可编辑稿件与结构化 result.json。
---

# 开题报告：研究缺口与证据提炼（Evidence-Grounded Gap Framing）

## 用途与适用边界

本 Skill 解决开题写作中最常见的失效模式——把“相关领域综述一遍”当作研究背景。核心方法：先把输入材料拆成编号证据，再由证据推导缺口，最后由缺口收敛出研究问题，使“背景真的指向缺口”可机器核验。

适用：给定科研材料（课题指南、前期数据、文献摘录、组内讨论纪要等）需要产出或修改开题报告/研究计划书的任务。
不适用：无任何输入材料、要求凭常识自由命题的任务（此时应索要材料或明确标注假设，见“异常处理”）。

## 运行契约（评测环境必读）

1. 读取 `/input/case.json` 与 `/input/task.md`，以二者为唯一事实来源。**禁止凭领域常识补造材料中没有的数据、引用或结论**；实际输入文件与原文是事实依据，不依据领域标签推断内容。
2. 在 `/app/work` 下完成草稿与中间产物；最终产物写入 `/app/output`。
3. 产出 `/app/output/result.json`，逐字段包含 `case.json` 中 `output_contract` 声明的全部键（键名完全一致），并额外包含 `case_id`、`status`（`success`/`partial`）、`artifacts`、`sources`、`uncertainty`、`change_log`。
4. 交付可编辑稿件 `proposal.md` 与 `proposal.docx`，并用本 Skill 的 `scripts/build_output.py` 渲染**真实** PDF 与首页 PNG 预览；渲染失败时如实降级为 `partial` 并记录原因，绝不伪造预览。
5. 材料缺失、口径冲突、需人工确认的内容：写入稿件第 10 章与 `result.json.uncertainty`，不得静默假设。
6. 预算约束（64 次模型请求、900 秒）：先产出可用的完整初稿并保存，再迭代改进。

## 工作流程

### 第 1 步：证据清单化（Evidence Register）
通读全部输入材料（含 PDF 时用 pdftotext 解析实际文本，不预置答案），把每条可用事实/数据/结论登记为 `E1…En`，逐条记录：内容摘要、来源文件与位置（页码/段落/表号）、可信度（材料明示/推断）。登记进 `/app/work/evidence_register.md`（模板见 `templates/evidence_register.md`）。材料中不存在的引用不得列入。

### 第 2 步：构建“已知—未知—待验证”矩阵
- 已知：只能来自证据清单，每条已知至少标注一个〔En〕。
- 未知/缺口：由已知之间的冲突、空白或矛盾推导，写明推导链（哪些已知 → 推出哪个未知）。无材料支撑的“缺口”标注为假设并列入人工确认项。
- 待验证：即本课题要回答的问题，与第 3 步研究问题一致。
使用 `templates/gap_matrix.md`。缺口陈述 1—3 条，宁精勿滥。

### 第 3 步：缺口收敛为研究问题
每个缺口对应 1 个可证伪的研究问题，写出否定判据（何种结果将推翻预期答案）。问题数量 1—3 个。

### 第 4 步：补齐其余六要素（对得上 / 排得开 / 说得清）
按 `templates/proposal_template.md` 完成研究目标、技术路线、阶段计划、风险、预期成果。对齐规则：目标↔问题一一对应；路线步骤↔目标一一对应；里程碑落在 case.json 给定的周期与经费内；每条风险含触发信号、备选方案、决策时点。引用文献一律来自材料，编号 [n] 与参考文献一一对应。

### 第 5 步：反综述自检
逐句检查背景章节：删除或改写与缺口无指向关系的句子；确认每个论断句尾有〔En〕或 [n] 标注；确认缺口陈述每条都有 ≥2 条已知证据支撑（若不足，如实降级并标注）。

### 第 6 步：构建、校验与交付
```bash
python3 scripts/validate_proposal.py /app/work/proposal.md --profile gap --report /app/output/validation_report.json
# 修复全部 hard_failures 后：
python3 scripts/build_output.py --work /app/work --out /app/output --case /input/case.json
```
将 `proposal.md` 复制到 `/app/work/proposal.md`（若草稿在别处），在 `/app/work/result_content.json` 中填写 `output_contract` 各字段的值（含 `uncertainty`、`change_log`、`sources` 列表）。

## 输出契约

| 产物 | 位置 | 要求 |
|---|---|---|
| 可编辑稿件 | `/app/output/proposal.md` / `.docx` | 七要素齐全；论断带证据编号 |
| 渲染预览 | `/app/output/proposal.pdf` / `proposal_preview.png` | 真实渲染；失败时降级 partial |
| 结构化结果 | `/app/output/result.json` | output_contract 全字段 + case_id + status + sources + uncertainty + change_log |
| 校验报告 | `/app/output/validation_report.json` | 由 validate 脚本生成 |

## 异常处理

- **材料缺失**（如无周期/经费/前期数据）：在稿件与 result.json 中以“待确认”占位，status=partial，uncertainty 说明缺什么、影响哪一章。
- **材料冲突**：并列呈现两种口径，标注来源，不擅自取舍。
- **缺口证据不足**：保留该缺口但显式标注“假设，需导师确认”，不得伪装成材料结论。
- **周期/经费明显不可行**：如实指出矛盾并给出可行化建议（压缩范围/延长周期），不得假装排得开。
- **引用无法获取**：不编造文献；缺失引用的论断改写为材料内证据支撑或删除。

## 资源文件

- `templates/evidence_register.md`、`templates/gap_matrix.md`、`templates/proposal_template.md`
- `checklists/quality_checklist.md`（A 组“立得住”为本版本重点核查项）
- `scripts/validate_proposal.py --profile gap`、`scripts/build_output.py`

## 最小调用示例（示意，非正式案例结果）

输入：`/input/case.json`（含 case_id、output_contract、材料清单与约束）、`/input/task.md`。
调用：Agent 按“工作流程”执行后，`/app/output/result.json` 示意：
```json
{"case_id": "example", "status": "success", "proposal": "proposal.md",
 "artifacts": ["proposal.md", "proposal.docx", "proposal.pdf", "proposal_preview.png"],
 "sources": ["E1: 材料A p.3", "[1]: 文献B"],
 "uncertainty": [], "change_log": ["v1 初稿"]}
```
（以上键以 case.json 的 output_contract 为准补充。）
