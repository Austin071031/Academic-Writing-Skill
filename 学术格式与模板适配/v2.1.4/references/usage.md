# 使用与方法说明（academic-format-adapter）

## 1. 适用场景

- 投稿稿件按期刊/会议模板 docx 适配（页面、字体、标题层级、题注、三线表、参考文献样式）。
- 学位论文按学校模板 docx 适配（页边距、行距、章节编号、目录、页码、题注位置）。
- 模板以 .tex/.cls 或格式说明文本/PDF 给出时的结构化规格提取与套用。
- 稿件为 .tex/.md/.pdf 时的转换 + 适配（PDF 为文本流重建，属有损降级）。

不适用于：需要重排版式结构（增删章节、合并表格）的内容编辑任务；需要修订模式追踪的协作改稿。

## 2. 依赖环境

| 依赖 | 必需性 | 用途 | 缺失时行为 |
|---|---|---|---|
| Python 3.8+ 标准库 | 必需 | 全部 OOXML/OPC 处理 | — |
| LibreOffice (soffice) | 推荐 | 渲染 PDF 预览、.doc/.odt 转换 | render 阶段标 partial，其他阶段照常 |
| poppler-utils | 推荐 | pdftotext / pdfinfo / pdffonts / pdftoppm（页面实测、字体嵌入、PNG 预览、目录页码回填） | 预览与字体核验降级 |
| pandoc | 可选 | .tex/.md/.txt 源稿转换 | 对应源格式无法处理时标 failed |

赛题环境（resources.yaml 的 office-renderer / scientific-python / pdf-text-tool / pdf-render-tool）已满足全部依赖。字体以环境提供的 Liberation Serif 为 Times New Roman 的度量兼容替换（官方 revision3 配置）。

## 3. 调用方式

### 3.1 一键（默认）

```bash
python3 /skills/weekly-skill/scripts/run_pipeline.py \
    --case /input/case.json --task /input/task.md \
    --work /app/work --outdir /app/output
```

### 3.2 分阶段（调试/人工介入时用）

```bash
python3 run_pipeline.py --stages inspect                          # 只解析案例
python3 inspect_case.py --case /input/case.json --out /app/work/plan.json
python3 measure_template.py TEMPLATE.docx --out /app/work/spec_template.json --checklist /app/work/checklist.md
python3 extract_spec.py --text /app/work/task_text.md --measured /app/work/spec_template.json --out /app/work/spec.json
python3 adapt_docx.py MANUSCRIPT.docx --spec /app/work/spec.json --out /app/output/manuscript_adapted.docx --changelog /app/work/changes.json
python3 fidelity_check.py ORIG.docx /app/output/manuscript_adapted.docx --report /app/work/fidelity.md --json /app/work/fidelity.json
python3 compliance_check.py /app/output/manuscript_adapted.docx --spec /app/work/spec.json --report /app/work/compliance.md
python3 render_preview.py render /app/output/manuscript_adapted.docx --outdir /app/output
python3 build_result.py --plan /app/work/plan.json --work /app/work --outdir /app/output
```

run_pipeline.py 的参数：`--manuscript PATH`、`--template PATH`（强制指定角色，跳过自动判定）、`--no-toc`、`--stages a,b,c`。

## 4. 输入输出

**输入**：`/input/case.json`（case_id、任务文本、materials、template、output_contract——键名做防御性多写法解析）、`/input/task.md`、材料文件（docx/tex/md/pdf/图片）。

**输出**（`/app/output/`）：

| 文件 | 说明 |
|---|---|
| `manuscript_adapted.docx` | 主产物，可编辑稿件（样式绑定结构化套用） |
| `manuscript_adapted.pdf` | 主产物的真实渲染（LibreOffice） |
| `preview-*.png` | 前 6 页渲染预览 |
| `render_report.json` | 页面尺寸实测、字体嵌入、渲染状态 |
| `result.json` | 结构化结果（见下） |

**`result.json` 字段**：`case_id`、`status`、`deliverables[]`、`output_contract_filled`（case 原契约全部字段→真实产物路径或 unresolved）、`verification`（合规汇总、保真结论、渲染状态）、`sources[]`、`changes[]`（单元级修改记录）、`uncertainty`（未决规格项、冲突、假设、备注）、`limits[]`、`stages`。

**过程产物**（`/app/work/`）：plan.json、spec_template.json、checklist.md、spec.json、changes.json、fidelity.md/json、compliance.md/json、stage_*.json。供复核"从输入件到成品"的完整链条。

## 5. 方法要点

1. **模板实测**：从模板 styles.xml / numbering.xml / sectPr 实测样式规格，不从经验猜；与任务文本冲突时文本优先、冲突登记。
2. **结构化套用**：标题层级用 styles.xml 样式绑定 + numbering.xml 抽象编号（目录、导航、大纲天然正确）；不用"只调字号加粗"。内嵌编号的标题段落自动抑制样式编号防止重复编号。
3. **内容零改动**：适配只动样式/页面/边框/页眉页脚，fidelity_check 以段落序列 + 单元格文本 + 媒体字节级比对证明零丢失；目录新增条目经 TOC1-3 样式结构豁免并登记白名单。
4. **导出核验**：页面尺寸 pdfinfo 实测、字体 pdffonts 检查嵌入、目录 TOC 域两遍渲染回填真实页码（Word 仍可 F9 刷新）。
5. **诚实降级**：阶段隔离，失败不中断；部分结果尽早落盘；状态如实。

## 6. 失败处理与自查

- 每阶段状态在 `/app/work/stage_*.json`；流水线打印 `[stage:名] success/partial/failed`。
- 自查顺序：`compliance.md`（是否逐项 PASS）→ `fidelity.md`（PASS/WARN/FAIL 及缺失单元）→ `render_report.json`（字体嵌入、页面尺寸）→ `result.json`（契约字段是否齐全）。
- 常见失败与处置见 SKILL.md「常见异常处理」与 references/troubleshooting.md。

## 7. 限制

- 复杂版式（多栏混排、文本框定位、化学结构式、数学公式位置调整）不自动处理；公式与图片原样保留。
- 参考文献不做重排（不重新排序、不改写条目内容），只做样式统一（悬挂缩进、字号），避免事实漂移。
- 多节文档（不同节不同页边距）目前只对末节 sectPr 生效，其余节保持原样并在 changes 注明。
- 题注重编号默认不自动执行（防止与正文交叉引用脱节），仅在 spec 明确要求时登记为待人工确认项。
- 扫描 PDF 判定后不再强行处理（OCR 不属于本 Skill 范围），如实报 failed。

## 8. 维护信息

版本：v1.0（2026-11）。文件：SKILL.md、scripts/*.py（10 个）、references/*.md（3 个）、examples/example.md。全部为 UTF-8 文本，无符号链接，无外部私有文件依赖。
