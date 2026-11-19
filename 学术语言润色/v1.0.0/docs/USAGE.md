# 使用与方法说明（USAGE）

面向复用者：把自己的稿件或学科文本交给加载本 Skill 的 Agent，按下列步骤执行；
脚本也可脱离 Agent 手工调用（分句、术语抽取、守恒检查对任意文本对适用）。

## 1. 快速开始

1. 准备输入目录：`case.json`（可含 `output_contract`）、`task.md`（润色要求与文体）、
   稿件文件（txt/md/tex/docx/pdf，可多个）。
2. 运行阶段0：`bash scripts/run_pipeline.sh /input /app/work /app/output`。
3. 按 SKILL.md 阶段1–7 执行（Agent 自动）或手工执行：逐句决策写入
   `work/polish_chunks/*.jsonl` → assemble → terminology check / guard_check →
   处置 resolutions → assemble → render_previews → validate_output。
4. 查看 `/app/output`：polished_full.md 为改后全文，change_log.md 为逐句说明，
   review_report.md 为审校证据，result.json 为结构化结果。

## 2. 输入要求与适用条件

- 文体：期刊论文、学位论文、基金申请书、审稿回复、英文摘要及一般学术段落。
- 语言：中文、英文及中英混排；日文在术语表登记后可混入处理。
- 不适合：整篇翻译（非润色）、文学创作、纯内容问答。
- 材料：优先纯文本/Markdown/LaTeX；docx 用标准库解析（复杂排版可能丢失）；PDF 依赖
  pdftotext/PyMuPDF，扫描件需 OCR（环境无 OCR 时如实标注）。

## 3. 关键方法（为什么这样设计）

| 方法 | 解决的问题 | 证据 |
|-|-|-|
| 带稳定 ID 的机械分句（extract_text.py） | 逐句对照可追溯、长文可分页处理 | source_dump.md 与 change_log 共用 ID |
| 术语表驱动（terminology.py build/check） | 同义混用、跨章漂移、缩写首现不规范 | consistency_report 列出每种写法的出现位置 |
| 限定强度/事实守恒检查（guard_check.py） | 润色中数值、引用、限定词被顺手改动 | guard_report 逐条列 original/polished 对照 |
| 最小编辑 + 逐句留痕 | 整段重写导致作者声音与限定词丢失 | change_log 每句 keep/modify + reason |
| 改写与审校双通道 + 回读校验 | 单通道自我修改无人复核 | resolutions.jsonl 记录每条 critical 去向 |
| 诚实降级（partial/uncertainty/null_reason） | 材料缺口与失败被掩盖 | result.json 固定字段，validate 强制 |

## 4. 用于自己的稿件（脱离评测环境）

```bash
mkdir -p /tmp/mywork/input && cp 我的稿件.md /tmp/mywork/input/
echo '{"case_id":"my-draft","output_contract":{}}' > /tmp/mywork/input/case.json
echo "按期刊论文语域润色，保持数值与引用不变。" > /tmp/mywork/input/task.md
bash scripts/run_pipeline.sh /tmp/mywork/input /tmp/mywork/work /tmp/mywork/output
# 然后手工写 polish_chunks 或用 Agent 执行 SKILL.md 阶段3
```

## 5. 限制

- 分句是启发式：引用、数学已保护，但极端嵌套结构可能需要人工微调 ID 对应。
- 守恒检查的限定词表覆盖常见档位，领域特有套语（如"显著"的统计义判定）需人工确认。
- docx 复杂表格/脚注可能丢失；PDF 两栏排版提取顺序可能错乱（-layout 模式已缓解）。
- 预览 PDF 需要环境有 CJK 字体；否则用 HTML 预览。

## 6. 自查清单（交付前）

- [ ] validate_output.py 退出码 0，result.json status=complete（或 partial 且原因写明）
- [ ] output_contract 每个键有 delivered 或 null_reason
- [ ] change_log 每条 modify 有受控类型与理由；keep 句有保留依据
- [ ] guard_report critical=0 或 resolutions 逐条记录；coverage=100%
- [ ] terminology check critical=0；冲突取舍写入 note
- [ ] uncertainty / manual_review_required 已更新
- [ ] 预览文件可用（HTML 至少可打开）

## 7. 失败处理

- 某脚本失败：先读其 stderr 与 work 目录下的报告文件；多数失败来自输入编码或缺失
  可选依赖，降级路径已在 SKILL.md"依赖与环境自适应"列出。
- 预算耗尽：按 edge_cases.md"预算兜底顺序"保存部分结果。
- 全部无法提取文本：result.json status=failed，uncertainty 写明原因，不编造内容。
