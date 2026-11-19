---
name: proposal-traceable-delivery
description: 为开题报告建立“论断—来源”逐条映射与引用一一对应核验，并通过 pandoc/libreoffice 管线交付可直接编辑的 markdown+docx、真实渲染的 PDF 与 PNG 预览、含修改记录与人工确认项的 result.json。适用于开题报告、研究计划书需要可追溯引用、可继续编辑交付、版本与边界明确的任务。
---

# 开题报告：引用溯源与可编辑交付（Traceable Delivery Pipeline）

## 用途与适用边界

评审与导师修改的前提是“每个论断能定位到输入材料、引用与版本，结果可继续编辑”。本 Skill 以**论断—来源映射表 + 渲染交付管线**为主工件：写作即编号、引用即核验、交付即可编辑文件加真实预览，版本与边界全程留痕。

适用：给定材料需产出/修改开题报告、研究计划书，且评分关注可核验性、可编辑交付的任务。
不适用：无材料自由命题；按异常处理索要材料或显式标注假设。

## 运行契约（评测环境必读）

1. 读取 `/input/case.json` 与 `/input/task.md` 为唯一事实来源；**禁止补造材料外数据、引用**；PDF 解析实际文本。
2. 中间产物 `/app/work`；最终产物 `/app/output`。
3. `result.json` 逐字段含 `output_contract` 全部键 + `case_id`、`status`、`artifacts`、`sources`、`uncertainty`、`change_log`；由 `scripts/build_output.py` 合并生成，不手写遗漏键。
4. 交付 `proposal.md` + `proposal.docx`（pandoc）+ `proposal.pdf`（libreoffice 真实渲染）+ `proposal_preview.png`（pdftoppm 首页）；任一步失败降级 `partial` 并记录原因，绝不伪造预览。
5. 缺口与冲突写入稿件第 10 章与 `uncertainty`。
6. 预算 64 请求、900 秒：先存完整初稿与初版 result.json，再迭代。

## 工作流程

### 第 1 步：写作即编号
按 `templates/proposal_template.md` 完成七要素全稿。规则：
- 材料事实标注证据编号〔E1〕…，本课题论断标注〔C1〕…；
- 文献引用用 [1]…[n]，只允许引用材料中实际给出或可核实的条目；
- 章节编号、表格编号全程保留（第 1—10 章结构），便于导师引用定位。

### 第 2 步：论断—来源映射表
逐条登记全文关键论断（模板 `templates/claim_source_map.md`）：论断编号、摘要、来源（〔En〕/[n]/“假设，待确认”）、所在章节、修改记录。材料中无来源的论断要么补来源，要么改写为假设并列入人工确认项，不得裸奔。

### 第 3 步：引用一一对应核验
双向核验（由 `scripts/validate_proposal.py --profile delivery` 执行并人工复核）：
- 正文每个 [n] 在参考文献表中存在；
- 参考文献每条至少被正文引用一次，未引用的移入“未采用文献”附注或删除；
- 每条文献信息（作者/题名/年份/出处）与材料原文一致，不得补全材料未给出的字段。

### 第 4 步：版本与边界留痕
维护 `change_log`（每轮修改：时间、改动章节、改动理由）与第 10 章“人工确认与材料缺口”（逐条列：缺什么、冲突双方、需谁确认）。修改记录同步写入映射表“修改记录”列。

### 第 5 步：构建交付
1. 填写 `/app/work/result_content.json`：`output_contract` 各字段值 + `sources`（材料位置与文献清单）+ `uncertainty` + `change_log`。
2. 执行：
```bash
python3 scripts/validate_proposal.py /app/work/proposal.md --profile delivery --report /app/output/validation_report.json
python3 scripts/build_output.py --work /app/work --out /app/output --case /input/case.json
```
3. 核对 `/app/output/result.json`：契约键齐全、status 诚实、artifacts 中预览文件真实存在。

## 输出契约

| 产物 | 要求 |
|---|---|
| proposal.md / .docx | 可继续编辑；章节编号、样式、表格完整 |
| proposal.pdf / proposal_preview.png | 真实渲染，供评审快速查验 |
| result.json | output_contract 全字段 + case_id + status + sources + uncertainty + change_log |
| validation_report.json | 引用双向核验与硬性检查结论 |

## 异常处理

- **材料未给参考文献信息**：不编造；正文相应论断改用证据编号〔En〕支撑，文献章写“材料未提供可核实文献”。
- **渲染工具缺失或失败**：保留 md/docx，status=partial，build_notes 记录失败命令与错误，不伪造 PDF/PNG。
- **docx 样式与 md 不一致**：以 md 为准重新渲染；仍不一致时在 change_log 记录差异。
- **output_contract 含无法填写的字段**：以 null 占位并写入 uncertainty，说明缺什么。

## 资源文件

- `templates/claim_source_map.md`、`templates/changelog.md`、`templates/proposal_template.md`
- `checklists/quality_checklist.md`（D 组“说得清”与 E 组“交付与运行”为重点核查项）
- `scripts/validate_proposal.py --profile delivery`、`scripts/build_output.py`

## 最小调用示例（示意）

`case.json` 的 output_contract 为 `{"proposal": ..., "risk_count": ..., "summary": ...}`。`/app/work/result_content.json` 填三者后，构建得到 `/app/output/result.json`：
```json
{"case_id": "example", "status": "success", "proposal": "proposal.md", "risk_count": 5,
 "summary": "……", "artifacts": ["proposal.md", "proposal.docx", "proposal.pdf", "proposal_preview.png"],
 "sources": ["E1: 材料A p.3", "[1]: 材料A 所附文献"], "uncertainty": ["阈值 t0 为假设值，待导师确认"],
 "change_log": ["v1 初稿：完成七要素"], "build_notes": []}
```
（键以实际 case.json 的 output_contract 为准。）
