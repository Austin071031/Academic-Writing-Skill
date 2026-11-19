# longdoc-dossier（学位论文与长文档写作 · 长上下文登记簿方向 v1.0.4）

## 用途
数万字分章节长文档续写时的「记得住前文」方案：把全文压缩成上下文登记簿
（dossier：定义 / 已下结论 / 材料使用矩阵 / 术语首现表 / 图表 caption），
为待写章节生成受字数预算约束的写作上下文摘要（context_brief），写完后复核
重复论述、重复结论、脱节（未定义缩写、悬空图表引用）与材料遗漏。
解决题面「写得长不脱节」：后写章节与前文定义、已用材料、已下结论保持可见性，
不脱节、不重复论述。

## 安装与调用
平台将本目录安装为 `/skills/weekly-skill` 后由 Agent 按 `SKILL.md` Phase 0-5 执行。
本地最小流程：

```bash
python3 scripts/init_result.py --case case.json --out output
python3 scripts/inspect_case.py --case case.json --task task.md --input-dir input --work work
python3 scripts/parse_chapters.py input/chapters/*.md input/materials/facts.md --work work
python3 scripts/dossier_engine.py build --chapters work/chapters.json --work work
python3 scripts/dossier_engine.py brief --dossier work/dossier.json \
  --target-section "第3章 结果与讨论" --budget-chars 3000 --work work
# Agent 只读 work/context_brief.md 写 draft_ch3.md（无需通读全文）
python3 scripts/dossier_engine.py overlap --draft work/draft_ch3.md \
  --chapters work/chapters.json --dossier work/dossier.json --work work
python3 scripts/assemble_result.py --work work --out output --case case.json \
  --skill "longdoc-dossier v1.0.4" --status success
python3 scripts/validate_output.py --out output --work work
python3 scripts/render_previews.py --out output
```

## 依赖
Python 3.8+ 标准库；共享脚本对 docx/pdf 材料分别用 zipfile 解析与 pdftotext
降级（缺失时如实记录 issues）。dossier_engine.py 自身零第三方依赖。

## 产物
| 文件 | 内容 |
|-|-|
| work/dossier.json + dossier.md | 上下文登记簿（定义/结论/材料使用/术语首现/caption） |
| work/context_brief.md | 目标章节的写作上下文摘要（预算约束 + 截断记录） |
| work/overlap_report.json + .md | 重复论述/重复结论/脱节/材料遗漏复核 |
| output/chapter_N.md | 通过复核的新章节稿 |
| output/result.json | 结构化结果（含 output_contract 全部字段） |

## 边界与已知限制
- 全部相似度为字符 n-gram 字面启发式（阈值见 references/dossier_rules.md）：
  语义复述但字面零重合的重复可能漏检；跨语言重复不检。
- 定义/结论靠模式匹配抽取，非常规表述会漏登记；dossier 为空类时如实显示「（无）」，
  不臆造。
- 未定义缩写检查只覆盖全大写缩写（≥2 字母），中文术语的「首次出现未定义」
  依赖 Agent 对照 dossier 定义表自查。
- 材料文件靠文件名提示词识别，识别不到时用 `--materials-regex` 指定。
