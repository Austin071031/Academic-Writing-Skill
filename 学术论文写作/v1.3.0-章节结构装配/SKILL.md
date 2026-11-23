---
name: structure-completeness-assembly
description: 章节结构与完整性装配专精的学术写作 Skill。当任务要求按学科规范/期刊模板组织论文章节、补齐缺失章节与声明字段、控制各节详略时使用，例如"按 IMRaD 结构写完整初稿""检查这篇稿子缺哪些章节""补数据可得性声明"。本 Skill 先生成"章节×支撑材料"装配骨架（哪节有材料、哪节是缺口一目了然），写作执行"缺项显式标注"红线（无材料的节标【待补】而非省略），成稿后机读五检：必备章节齐全、声明字段（数据可得性/利益冲突/作者贡献/基金）、标题层级连续、图表注存在、篇幅比例合理。输出 /app/output 的 result.json（含 output_contract 全部字段）、manuscript.md/docx、PDF/PNG 预览、completeness_report.md。适用于有材料、有明确体裁/模板约束的全稿或章节写作。
---

# 章节结构与完整性装配 Skill（全得起专精）

核心原则：**骨架先行、缺项不省略只标注、声明字段必查、详略按比例**。

## 适用与不适用
- 适用：IMRaD 全稿/单章写作、模板适配（摘要/引言/方法/结果/讨论/结论/参考文献/声明）、双语结构对齐、章节缺项体检。
- 不适用：无材料自由写作（材料全缺按异常 partial 退出并说明）。

## 输入与输出
- 输入：`/input/case.json`、`/input/task.md`、科研材料。
- 输出（`/app/output/`）：`result.json`（含 output_contract 全部字段+case_id）、`manuscript.md`（+docx/pdf/preview）、
  `completeness_report.md`、`engine_report.json`、`run_log.md`。
- 中间产物：`/app/work/outline.md`（章节×材料骨架）、brief.json、sections/。

## 执行流程（严格按序，写稿优先）

### 0. 预处理（一条命令）
```bash
bash /skills/weekly-skill/scripts/run.sh pre
cat /app/work/brief.json /app/work/outline.md
```
得到 brief（必备章节/字数/引用格式）与**装配骨架**：每个必备章节的支撑材料、建议篇幅、材料缺口。
此时 result.json 已有保底骨架。

### 1. 写稿（预算主要部分）
按 outline.md 逐节写 `/app/work/sections/NN-*.md`，`cat` 合并为 manuscript.md。结构红线（详见 references/section_templates.md、references/declarations.md）：
1. **必备章节一个不少**：brief.required_sections 每节都有对应标题（中英文均可）；**无材料的节不得省略**，
   写 `## 该节名\n\n【待补：缺材料（具体缺什么）】` 并列入 uncertainty。
2. **声明字段必查**：数据可得性、利益冲突、作者贡献、基金资助、致谢——任务或模板要求时逐条落实，
   材料未提供写【待确认：材料未提供××声明】。
3. **标题层级连续**：# → ## → ### 不跳级；图注表注编号连续且正文有引用。
4. **详略按比例**：摘要≈5%、引言≈15%、方法≈25%、结果≈30%、讨论≈20%（按 word_target 折算，±30% 可接受）；
   材料不足以支撑目标字数时写满事实为止，uncertainty 说明实际字数与原因，**不注水**。
5. 摘要四要素（目的-方法-结果-结论）、无引用编号、数字与结果节一致。
6. 数字/引用事实红线同通用规范：只用材料中的数值与文献，缺失标【待确认】。

### 2. 核验与收尾（一条命令）
```bash
bash /skills/weekly-skill/scripts/run.sh post
cat /app/output/completeness_report.md /app/output/validation.md
```
机读五检：必备章节（无【待补】标注的缺失=FAIL）、标题跳级、篇幅偏离、摘要引用、显式缺口清单。
FAIL 必须返修后重跑 post；全部 PASS/WARN 方可 success。

## 异常处理
| 情况 | 处置 |
|-|-|
| 任务未明示章节要求 | 用 brief 推断的 IMRaD 默认结构，run_log 注明"章节为推断" |
| 材料与模板冲突（材料只有结果数据） | 保留模板结构，无材料节标【待补】，不删节 |
| 字数严重不达标 | 写满事实为止，uncertainty 说明；禁止注水凑字 |
| 双语任务 | 中英逐节对应，章节数一致，术语一致 |
| pandoc/libreoffice 缺失 | 只交付 md，预览标 unavailable |

## 预算纪律
pre/post 纯脚本各 <2 分钟；写作按节落盘先完整后润色；核验 FAIL 优先补节而非重写。

依赖：python3≥3.9（纯标准库）；pdftotext/pandoc/LibreOffice/pdftoppm 可选降级。
