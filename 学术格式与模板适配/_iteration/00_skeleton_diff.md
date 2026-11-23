# 表 3 · 版本骨架对照（学术格式与模板适配）

来源：`git clone` 实读（2026-11-23，commit 84180db + ec36a5a）。

## 共有文件（= 基线资产白名单取数依据）

v1.0.0 与 v1.0.1 **完全一致**的文件：

| 文件 | 作用 |
|-|-|
| `SKILL.md` | Agent 入口指令：运行时契约、一键流水线、人工复核点、铁律、异常处理 |
| `scripts/ooxml.py` | OPC/OOXML 底层：schema 顺序插入、rels/内容类型注册（默认命名空间）、ET 写穿缓存 |
| `scripts/inspect_case.py` | case.json/task.md → plan.json（防御性键名解析、路径解析、材料角色分类） |
| `scripts/measure_template.py` | 模板 docx 实测 → spec_template.json + checklist.md |
| `scripts/extract_spec.py` | 任务文本/tex/cls/pdf → spec.json（合并实测、冲突登记、中文字号表） |
| `scripts/adapt_docx.py` | 结构化套用：页面/样式绑定/标题编号/三线表/题注/参考文献/页脚页码 |
| `scripts/fidelity_check.py` | 内容单元级保真比对（段落序列、单元格、媒体字节、域/链接/脚注计数） |
| `scripts/compliance_check.py` | 逐项合规核验（PASS/FAIL/SKIP + 实测值） |
| `scripts/render_preview.py` | LibreOffice 渲染 + pdfinfo/pdffonts/pdftoppm + TOC 插入与两遍页码回填 |
| `scripts/build_result.py` | result.json 组装（契约字段填充、状态、sources/changes/uncertainty/limits） |
| `scripts/run_pipeline.py` | 九阶段编排、阶段隔离降级、源格式转换（pandoc/LO/PDF 文本重建） |
| `references/usage.md` | 使用与方法说明 |
| `references/spec_schema.md` | spec.json 规格字典 |
| `references/troubleshooting.md` | OOXML/OPC 12 条坑位备忘 |
| `examples/example.md` | 最小调用示例（示意） |

## 各版独有 / 差异

| 差异 | v1.0.0 | v1.0.1 |
|-|-|-|
| `scripts/build_result.py` | 契约字段映射仅精确键+包含 | 增加语义别名词重叠打分（ALIASES） |
| README/CHANGELOG/SUBMISSION | 各自版本记录 | 同 |

## 基线资产白名单（禁改/只可加）

R1–R10（自检与守恒规则，取自实际代码行为）：

- R1 `ooxml.py`：pPr/rPr/style/lvl/sectPr 子元素 canonical 顺序插入与保存前排序
- R2 `ooxml.py`：.rels / [Content_Types].xml 默认命名空间序列化；rels Target 相对 word/
- R3 `adapt_docx.py`：标题样式绑定 + numbering.xml 抽象编号；内嵌编号段落 numId=0 抑制
- R4 `adapt_docx.py`：正文 run 归一化跳过 hyperlink/fldSimple/ins/del 内部
- R5 `fidelity_check.py`：原文段落为成品段落的有序子序列；媒体字节一致；TOC1-3 样式结构豁免
- R6 `compliance_check.py`：页边距/字号/行距/分栏/三线表/题注/参考文献/页码逐项实测核验
- R7 `render_preview.py`：两遍渲染回填 TOC 真页码；pdfinfo 实测页面尺寸；pdffonts 嵌入检查
- R8 `run_pipeline.py`：阶段隔离，失败降级继续，必写 result.json
- R9 `build_result.py`：result.json 含 case_id + 全部 output_contract 字段 + status/sources/changes/uncertainty/limits
- R10 全部脚本纯标准库，无 pip 依赖

## 跨题资产盘点（L4 候选，本仓库其他题目已实现、本题未用）

| 资产 | 来源题目 | 本题是否已用 |
|-|-|-|
| `direction.json` 方向元数据（脚本真读取） | 文献证据驱动写作 v1.0.x–v2.0.x | ❌ 未用 → v2.0.0 补 |
| `_iteration/` 迭代台账目录 | 文献证据驱动写作 | ❌ 未用 → 本次补 |
| init_result 先行写合法 result.json（§4-4） | 多题目 SKILL.md 约定 | 部分（末阶段才写）→ v2.0.0 修复为"inspect 后即写" |
