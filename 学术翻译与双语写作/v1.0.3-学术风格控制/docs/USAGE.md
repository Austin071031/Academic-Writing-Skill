# 使用与方法说明 — academic-style-control v1.0.3

## 完整调用步骤

| 步骤 | 命令 / 动作 | 输入 → 输出 | 说明 |
|-|-|-|-|
| 1 | `init_result.py` | → result.json 骨架 | 防超时空手 |
| 2 | `inspect_case.py --work $W` | /input → inspection.json | 方向/形态/材料 |
| 3 | `parse_manuscript.py --work $W` | 稿件 → structure.json | 稳定 ID |
| 4 | `segment_builder.py --work $W` | → segments.json | 句段分类+受保护片段 |
| 5 | Agent 分批翻译 | → translations.jsonl | 翻译期即守 style_rules |
| 6 | `assemble_translation.py` | → translation_full.md / bilingual.md | 缺译标记+溯源 |
| 7 | `style_engine.py audit --work $W` | → style_report.json + findings.json | 指标+逐句段问题+改写指令 |
| 8 | Agent 风格修订 | → 追加修订 → 重跑 6、7 | 高严重度清零；metrics 改善留痕 |
| 9 | report_builder → assemble_result → validate_output → render_previews | → /app/output | 报告、契约、闸门、预览 |

## 关键方法

1. **双维机检**：A 类直译痕迹（translationese：动词名词化、被动滥用、超长前置定语、
   英式连接、中式套话）与 B 类语域越界（宣传口吻、口语化、第一人称单数、感叹号）。
2. **量化指标**：中译目标的“的/百字”“被/百字”密度与长句分布；阈值见
   style_rules.md，指标异常时即使单条命中少也提示整体直译腔。
3. **改写指令到人**：每条 issue 附具体改写范式（如“进行了研究→研究了”），
   Agent 执行改写而非脚本自动替换——避免机械替换破坏语义。
4. **修订留痕**：assemble_translation 自动 diff 前后译文进 change_log，
   风格改进可在 report 中量化呈现。

## 适用场景与限制

- 适用：论文翻译稿润色、双语写作语气统一、学位论文中译英风格修正。
- 限制：规则库不穷尽；学科文体惯例（数学"we"、医学被动）由 Agent 调整。

## 失败处理与自查

- 自查：`validate_output.py` PASS；style_report 高严重度（宣传口吻等）清零；
  中低严重度逐条有处置（修订或驳回附理由）；metrics 在阈值内或已说明。
- 常见失败：把风格修订做成内容改写（红线 1，数字/术语/引用不得动）。

## 最小示例

见 `examples/minimal_example.md`（合成，标注“示例”）。
