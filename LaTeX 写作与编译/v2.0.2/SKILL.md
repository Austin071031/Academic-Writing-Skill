---
name: latex-template-reproducible-build
description: >-
  LaTeX 模板适配与可重复构建：把稿件迁入期刊/会议/学位论文模板并满足版式与必填项、
  审计导言区宏包冲突与加载顺序、修复编译错误、生成构建清单使他人可按记录的环境与
  命令得到同一产物；v2.0.2 增量为 pdf_extract PDF 材料直通（pdftotext 抽取 +
  章节/参考文献骨架重建）。当任务要求模板迁移、版式合规检查、构建工程化或可复现性
  说明时触发。不适用于：无 LaTeX 源码且不要求 LaTeX 产物的任务。产物：模板审查报告、
  适配后的可编译工程、PDF 预览、BUILD_MANIFEST 复现清单、结构化 result.json。
---

# latex-template-reproducible-build：模板适配 + 复现得了（v2.0.2：+PDF 材料直通）

核心理念：模板适配的本质是"稿件内容 × 模板约束"的差集管理——必填项、宏包边界、
版式机制逐项对齐；可重复构建的本质是"环境、命令、轮次、源码哈希"四项留证。
脚本做机读审计与清单生成，你（Agent）做迁移决策与内容回填（内容只来自材料）。

## 0. 触发与不触发

- 触发：任务要求把稿件迁入指定模板（材料含 .cls/.sty 或模板示例 .tex）、检查模板
  合规、整理导言区、或要求交付可复现的构建说明。
- 不触发：材料无 LaTeX 源且不要求 LaTeX 产物 → 按 Phase 0/5 交付诚实 partial。
- 材料只有目标模板的官网说明而无文件：按其文字约束做源码级合规，记 uncertainty
  （无法编译验证模板行为）。

## 1. 三条红线

1. **内容只来自材料**：迁入模板时的标题/作者/单位/摘要/关键词从稿件原文回填；
   材料没有的元数据建 TODO 占位并记 manual_confirmations，禁止编造。
2. **不盲目复制模板导言区**：只补任务/模板明确需要的；每个新增宏包记 change_log
   （用途与依据）；发现冲突对按模板说明取舍。
3. **版本与命令如实记录**：BUILD_MANIFEST 的版本号只能来自真实 `--version` 输出与
   编译日志；取不到写 "unknown"，禁止编造版本号。

## 2. 运行时契约速览

输入 /input/case.json + task.md + 材料；工作 /app/work；交付 /app/output
（result.json 含 case_id + output_contract 全部字段）。预算 64 请求/900 秒。
$S=/skills/weekly-skill/scripts，纯标准库。

## 3. 阶段流程

### Phase 0 — 保底与侦察

```sh
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md \
    --input-dir /input --work /app/work
```

- 读 inspection.tex_project：documentclass、packages、missing_refs（.cls/.sty 缺失
  是模板任务的头号障碍）。
- 识别模板材料：材料中的 .cls/.sty/模板示例 .tex（mains_candidates 中除稿件主文件
  之外的文件常是模板示例）；把模板路径记入 work/task_items.md。

### Phase 0.5 — PDF 材料直通（v2.0.2 增量，仅当 inspection.main 为空）

若 Phase 0 侦察未发现任何含 \documentclass 的主文件而材料含 PDF（契约明示
"PDF parsing receives the actual PDF"）：

```sh
python3 $S/pdf_extract.py --work /app/work
```

- 脚本调 pdftotext 抽取全文到 work/pdf_text.txt，重建可编译骨架 project/main.tex
  （章节/参考文献带行号锚点），并登记 manual_confirmations（作者/公式/图表为 TODO 占位）。
- pdftotext 缺失或抽取失败：exceptions 已登记，退回人工用环境内 PDF 工具读文本，
  不得伪造抽取结果。
- 骨架生成后进入 Phase 1 的正常闭环（审计/编译/验证）；你负责对照 pdf_text.txt
  把 TODO 逐项回填为真实内容——数字与公式以 PDF 为唯一事实来源，看不清记 uncertainty。

### Phase 1 — 模板审计 + 基线编译

```sh
python3 $S/template_audit.py --work /app/work --template <模板目录或示例.tex>
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
python3 $S/tex_logscan.py --work /app/work --top 10
```

读 work/template_report.json：
- P1 必填元数据缺失（按 documentclass 识别：IEEEtran/elsarticle/acmart/ctexart 等）；
- P2 宏包冲突对（natbib×biblatex、subfigure×subcaption、inputenc×xelatex 等）；
- P3 加载顺序（hyperref 未置末、cleveref 早于 hyperref）；
- P4 过时宏包/命令（epsfig、subfigure、{\bf ...}）；
- P5 与模板的差异（模板已载而稿件缺失的宏包、模板规定的 \bibliographystyle）。
- 基线编译失败先按 log_report 根因修通（缺 .cls 见异常表）。

### Phase 2 — 迁移与适配（逐项对齐）

按 task_items.md 与 template_report 逐项处理，每批 ≤5 处、改完复编：

1. **换类**：`\documentclass{...}` 换为目标类（选项按任务）；原类专属命令
   （如 article 的 \maketitle 参数差异）逐一映射，记 change_log。
2. **必填项回填**：标题/作者/单位/摘要/关键词/CCS/基金按模板命令从原文回填；
   原文没有的记 manual_confirmations + TODO 占位。
3. **导言区整理**：按 P2/P3/P4 处置冲突、顺序、过时项；P5 差异按需补载
   （不盲目全量复制模板导言区）。
4. **结构映射**：摘要/关键词环境、致谢、附录、参考文献样式按模板机制改写；
   模板自带的示例内容（dummy text）必须删除并记 change_log。
5. **版式自查**：字号/行距/页边距属模板类职责，不要手工 \usepackage{geometry}
   覆盖模板版式（除非任务明确要求，记 change_log）。

### Phase 3 — 收敛编译验证

```sh
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag final --until-converge --timeout 150
python3 $S/tex_check.py --work /app/work
python3 $S/template_audit.py --work /app/work --template <模板>
```

验收：final.success=true 且 converged=true（或逐项说明）；template_report 的 error
级清零；tex_check 的 undefined_*/placeholders 清零或登记；目视 preview.pdf
（首页元数据区、摘要、版式）与模板示例一致。

### Phase 4 — 构建清单（复现得了）

```sh
python3 $S/build_manifest.py --work /app/work
```

- 生成 work/build_manifest.json 与 work/BUILD_MANIFEST.md：引擎与工具版本
  （真实 --version）、宏包/类版本（编译日志解析）、源码文件 sha256、精确编译
  命令序列与轮次、收敛状态。
- 检查清单可读性：他人拿到 latex_project/ + BUILD_MANIFEST.md 应能直接复现；
  若依赖系统级宏包（TeX Live 年度版本），在清单"复现注意"中写明。

### Phase 5 — 交付

写 work/evidence_map.json（每项适配←→P 类 finding/模板要求）、change_log.json、
uncertainty.json、manual_confirmations.json、exceptions.json、stats.json：

```sh
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-template-reproducible-build v1.0.4" --status success   # 或 partial
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

assemble 会把 BUILD_MANIFEST.md 一并复制到 /app/output/reports/。

## 4. 异常处置表

| 异常 | 处置 |
|-|-|-|
| 模板 .cls/.sty 缺失 | 材料目录搜一遍；无则用功能最接近的可用类兜底，记 uncertainty（版式不保真）+ change_log |
| 模板要求字段材料无 | TODO 占位 + manual_confirmations；不编造 |
| 模板与任务冲突 | 以 task.md 为准，记 uncertainty 说明取舍 |
| 宏包冲突无法两全 | 按模板说明取舍；模板无说明按 references/template_rules.md 的推荐项，记 change_log |
| 引擎与模板不符 | 模板示例为 pdflatex 而稿件中文：优先 xelatex+ctex 兼容方案，记 uncertainty |
| 无 TeX 引擎 | 记 exceptions；仅静态审计交付 partial；BUILD_MANIFEST 标注"未能编译验证" |
| 版本信息不可得 | manifest 写 "unknown" 并注明来源缺失；不编造 |
| 预算告急（请求>32） | 停止适配，当前状态走 Phase 3-5 交付 partial |

## 5. 预算兜底

Phase 0-1 ≤8 请求；Phase 2 每批 2 请求；Phase 3-5 预留 ≥8（含 manifest 与交付）。
template_audit 幂等可复扫，error 数下降为进度信号。

## 6. work/ 中间文件格式

- change_log.json：`[{"op":"template_migrate","file":"main.tex","line":1,
  "before":"\\documentclass{article}","after":"\\documentclass[conference]{IEEEtran}",
  "reason":"任务要求迁入 IEEE 会议模板","evidence":"task_items.md 第1条"}]`
- stats.json：`{"p1_missing_initial":N,"p_errors_final":M,"conflicts_resolved":K,
  "manifest_files":F,"converged":true}`

## 7. 参考文件（按需取读）

- references/template_rules.md — P1-P5 判据、常见类必填项表、迁移范式
- references/failure_modes.md — 已知失败模式
- examples/minimal_example.md — 合成示例（非正式案例结果）
