---
name: academic-format-adapter
description: 学术格式与模板适配（academic manuscript format & template adaptation）。当任务要求把论文/学位论文稿件按投稿模板或格式规范重新排版时使用：从模板文件与任务文本实测提取格式规格（页边距、字号、行距、标题层级、题注、三线表、参考文献样式、页眉页脚、目录），以结构化样式绑定方式改造 DOCX（不删除、不合并、不改写、不图片化内容），自动逐项合规核验与内容单元级保真度比对，导出可编辑 DOCX + 真实渲染 PDF/PNG 预览 + 诚实 result.json（含 case_id、全部 output_contract 字段、状态、来源、变更记录、不确定性）。支持 docx/tex/md/pdf 输入与 docx/dotx/tex/cls/pdf/md 模板；纯 Python 标准库实现，无 pip 依赖。
---

# 学术格式与模板适配

把一份真实学术稿件按目标模板/格式规范改到**可交付**，并产出**可复核的证据链**：检查项清单（模板实测）→ 结构化套用（样式绑定而非外观模仿）→ 保真度核验（内容单元零丢失）→ 导出核验（字体嵌入、页面实测、目录页码）→ 诚实 `result.json`。

## 运行时契约（Harbor）

- 输入：`/input/case.json`、`/input/task.md`（材料路径以 case.json 为准；PDF 无预抽取答案层，须读真实文件）。
- 工作区 `/app/work`；最终产物与可编辑源文件放 `/app/output`。
- **`/app/output/result.json` 必须存在**，含 `case_id` 与 case 原 `output_contract` 的全部字段、诚实的 `status`（success/partial/failed）、`sources`、`changes`、`uncertainty`。
- 可编辑 Office 产物必须附带真实渲染 PDF/PNG 预览。预算有限：尽早保存诚实部分结果，再迭代改进。
- 不得伪造软件状态、数据或评测分数。

## 一键流水线（默认入口）

```bash
SKILL=/skills/weekly-skill   # 本 Skill 安装目录；不存在时先 find / -name run_pipeline.py
mkdir -p /app/work /app/output
python3 $SKILL/scripts/run_pipeline.py \
    --case /input/case.json --task /input/task.md \
    --work /app/work --outdir /app/output
```

流水线自动执行九个阶段，任何阶段失败都会降级并继续，最后**必定写出诚实 result.json**：

| 阶段 | 脚本 | 产出（/app/work 或 /app/output） |
|---|---|---|
| inspect | `inspect_case.py` | plan.json（case_id、材料角色、output_contract 原文） |
| measure | `measure_template.py` | spec_template.json + checklist.md（模板实测检查项清单） |
| spec | `extract_spec.py` | spec.json（模板实测+任务文本抽取合并，冲突与未决项登记） |
| convert_source | run_pipeline 内置 | .tex/.md/.pdf/.doc 源稿转为 docx（PDF 为文本流重建，标注有损） |
| adapt | `adapt_docx.py` | /app/output/manuscript_adapted.docx + changes.json |
| fidelity | `fidelity_check.py` | fidelity.md/.json（内容单元级前后比对） |
| compliance | `compliance_check.py` | compliance.md/.json（逐项 PASS/FAIL/SKIP） |
| render | `render_preview.py` | /app/output/*.pdf + preview-*.png + render_report.json；需要目录时两遍渲染回填真页码 |
| result | `build_result.py` | /app/output/result.json |

## 你的职责（流水线之间的人工判断点）

流水线跑完后**不要直接结束**，按顺序完成三项复核（各用 1-2 次请求即可）：

1. **复核 spec.json**：读 `/app/work/spec.json` 与 `/app/work/plan.json`。对照 case 任务文本，把 `unresolved` 中的缺项（如缺失的页边距/字号）按任务文本补齐；把 `conflicts` 中明显的解析错误（如把"三号黑体"误当正文规格）改对。修改 `spec.json` 后重跑：
   ```bash
   python3 $SKILL/scripts/run_pipeline.py --work /app/work --outdir /app/output \
       --stages adapt,fidelity,compliance,render,result \
       --case /input/case.json --task /input/task.md
   ```
   （重跑时先复制上一次 spec 不会被覆盖：`extract_spec` 只在 `spec` 阶段重写 `spec.json`；不带 `spec` 阶段即可保留你的修改。）
2. **处理 compliance.md 的 FAIL 项**：所有 FAIL 先查原因——若是 spec 解析错误，改 spec.json 重跑；若是稿件本身结构问题（如无标题样式无法判定层级），在 result.json 的 `uncertainty.notes` 中如实登记，不得假装通过。
3. **核对 result.json**：确认 `case_id` 非空（空则从 case.json 原文找到真实标识回填）、`output_contract_filled` 每个字段都有真实产物路径、PDF/PNG 预览真实存在。缺失则补跑对应阶段或如实标 partial/failed。

## 铁律（评分红线）

- **转得全**：禁止删除/合并/改写/图片化任何内容单元（正文、图表、公式、脚注、批注、修订、域代码、目录）。只改样式与页面设置；文字改动仅限题注编号规范化并须登记 changelog。
- **认得准**：格式数值一律来自模板实测或任务文本抽取，冲突在 spec.json 的 `conflicts` 登记（文本要求优先），绝不凭经验猜。
- **排得对**：标题层级走 styles.xml 样式绑定 + numbering.xml 编号，不只调字号加粗；表格三线表按 1.5pt 顶底框线 + 0.75pt 表头线 + 表头跨页重复实现。
- **交得出**：可编辑 DOCX 保留为交付源文件；PDF 由 LibreOffice 真实渲染并实测页面尺寸与字体嵌入（pdffonts 行尾右对齐解析，`Type 1`、`CID Type 0` 等多词类型不误判为未嵌入）；目录为 Word 可 F9 刷新的 TOC 域，页码经两遍渲染回填。
- **诚实**：模板缺失、扫描 PDF、材料冲突、无法判断分别说明；状态只写 success/partial/failed 的真实值。

## 环境与降级

- 纯 Python 3 标准库（zipfile + ElementTree），**无 pip 依赖**。可选外部工具：LibreOffice（渲染）、poppler（pdftotext/pdffonts/pdftoppm/pdfinfo）、pandoc（tex/md 转换）。缺失时自动降级并在 result.json 注明。
- 字体：模板要求 Times New Roman 而环境无该字体时，docx 中保留指定字体名（可移植性），渲染时 LibreOffice 自动度量兼容替换为 Liberation Serif（本赛题环境官方配置），结果在 render_report.json 记录。
- 扫描 PDF（抽取文本 < 400 字符）判定后如实报 failed + 原因，不装作成功。

## 常见异常处理

| 异常 | 处置 |
|---|---|
| /input/case.json 不存在 | 流水线从 task.md 合成案例描述并注明；材料经 /input 文件扫描兜底 |
| 模板为非 docx（tex/cls/pdf/md） | measure 跳过，spec 由文本/cls/pdf 抽取，checklist 仍输出 |
| 稿件为 PDF | 文本流重建 docx，标 partial；< 400 字符判扫描件，标 failed 并说明 |
| LibreOffice "source file could not be loaded" | 多为 OOXML 顺序/关系问题；本 Skill 的 ooxml.py 已按 schema 顺序插入与排序，若仍出现，检查你手工改过的文件 |
| 无标题样式无法识别层级 | 按文本模式（第X章/N.N/Abstract 等）判定，结果与置信度写入 uncertainty |
| output_contract 字段无法对应产物 | 如实标 unresolved + 人工确认说明，不得编造 |

## 资源索引

- `references/usage.md`：完整使用与方法说明、输入输出、适用场景、限制与自查方法。
- `references/spec_schema.md`：spec.json 规格字典与检查项清单语义。
- `references/troubleshooting.md`：OOXML/OPC 实战坑位与环境备忘（含字体替换、LibreOffice 行为）。
- `examples/example.md`：最小调用示例（示意输出，非正式案例结果）。
