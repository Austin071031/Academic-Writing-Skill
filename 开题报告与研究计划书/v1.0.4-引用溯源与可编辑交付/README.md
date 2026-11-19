# v1.0.4 引用溯源与可编辑交付 — 使用说明

## 这个 Skill 做什么
为开题报告建立“论断—来源”逐条映射与引用双向核验（正文 [n] 与参考文献一一对应），并通过 pandoc→libreoffice→pdftoppm 管线交付可编辑 markdown/docx、真实渲染 PDF 与首页 PNG 预览、含修改记录与人工确认项的 result.json。

## 调用方式
1. 准备 `/input/case.json`、`/input/task.md`。
2. 按 `templates/proposal_template.md` 撰写 `/app/work/proposal.md`，按 `templates/claim_source_map.md` 登记论断映射，`templates/changelog.md` 维护修改记录。
3. 填写 `/app/work/result_content.json`（output_contract 各字段 + sources + uncertainty + change_log），然后：
   ```bash
   python3 scripts/validate_proposal.py /app/work/proposal.md --profile delivery --report /app/output/validation_report.json
   python3 scripts/build_output.py --work /app/work --out /app/output --case /input/case.json
   ```
4. 核对 `/app/output/result.json`：契约键齐全、status 诚实、预览文件真实存在。

## 关键方法
- 写作即编号：材料事实〔En〕、本课题论断〔Cn〕、文献 [n] 三套编号互不混用。
- 引用双向核验：正文每个 [n] 有文献条目、每条文献至少被引用一次、文献字段与材料原文一致。
- 诚实渲染：工具缺失或失败即降级 partial 并记录命令与错误，不伪造预览。

## 适用边界
材料未提供可核实文献时不编造，论断改用证据编号支撑并在文献章说明。

## 失败处理与自查
见 `SKILL.md` 异常处理；自检重点：映射表无裸奔论断、无未引用文献、预览真实。
