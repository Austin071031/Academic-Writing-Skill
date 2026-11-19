# 学术格式与模板适配 · v1.0.1

玻尔产品周赛第四期「学术格式与模板适配」（challenge-96263d10）参赛 Skill
（attempt v1.0.1 二次提交）。把真实学术稿件按目标模板/格式规范改到可交付，并产出可复核的证据链。

## 能力概览

| 环节 | 做法 |
|---|---|
| 认得准 | `measure_template.py` 从模板 docx 的 styles/numbering/sectPr 实测提取检查项清单；`extract_spec.py` 从任务文本/tex/cls/规格 PDF 抽取结构化规格；冲突登记、文本优先 |
| 排得对 | `adapt_docx.py` 样式绑定（Heading1-4 + outlineLvl + numbering.xml 抽象编号）、页面设置、三线表（1.5/0.75pt）、题注样式、参考文献悬挂缩进、页脚页码域；标题内嵌编号自动抑制样式编号防重复 |
| 转得全 | `fidelity_check.py` 段落序列 + 表格单元格 + 图片字节级 + 公式/超链接/书签/脚注/批注/修订/域计数逐项比对，目录新增按 TOC1-3 样式结构豁免并登记白名单 |
| 交得出 | 可编辑 DOCX 为交付源；LibreOffice 真实渲染 PDF + PNG 预览；pdfinfo 实测页面尺寸、pdffonts 核验字体嵌入；目录 TOC 域两遍渲染回填真页码（Word 可 F9 刷新） |
| 诚实 | 阶段隔离降级；扫描 PDF 判 failed 并说明；result.json 含 case_id、全部 output_contract 字段、status/sources/changes/uncertainty/limits |

## 技术特征

- **纯 Python 标准库**（zipfile + ElementTree），无 pip 依赖；LibreOffice/poppler/pandoc 缺失时自动降级并注明。
- OOXML/OPC 坑位全部内置处理：schema 元素顺序、rels 默认命名空间与相对 Target、内容类型注册、ET 树写穿缓存（见 references/troubleshooting.md）。
- 九阶段流水线（inspect→measure→spec→convert→adapt→fidelity→compliance→render→result），任何阶段失败不中断，必定写出诚实 result.json。

## 文件

```
SKILL.md                 Agent 入口指令
scripts/                 10 个脚本（ooxml 底层 + 8 个阶段 + 总编排）
references/usage.md      使用与方法说明（调用、输入输出、限制、失败处理）
references/spec_schema.md spec.json 规格字典与检查项语义
references/troubleshooting.md OOXML/OPC 实战坑位与环境备忘
examples/example.md      最小调用示例（示意输出，非正式案例结果）
```

## 一键调用（运行时）

```bash
python3 /skills/weekly-skill/scripts/run_pipeline.py \
    --case /input/case.json --task /input/task.md \
    --work /app/work --outdir /app/output
```
