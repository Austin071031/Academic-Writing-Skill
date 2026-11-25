# 使用与方法说明 — editable-deliverables-plus v2.0.3

## 完整调用步骤

| 步骤 | 命令 / 动作 | 输入 → 输出 | 说明 |
|-|-|-|-|
| 1 | `init_result.py` | → result.json 骨架 | 防超时空手 |
| 2 | `inspect_case.py --work $W` | /input → inspection.json | 翻译方向、材料清单与哈希 |
| 3 | `parse_manuscript.py --work $W` | 稿件 → structure.json | 稳定 ID（SEC/P-s） |
| 4 | `segment_builder.py --work $W` | → segments.json | 句段分类+受保护片段 |
| 5 | `number_engine.py ledger --work $W` | → number_ledger.json | 译前数字台账：值/单位/原文形态逐句段列出 |
| 6 | Agent 分批翻译 | → translations.jsonl | 对照台账逐值落地；追加式 |
| 7 | `assemble_translation.py` | → translation_full.md / bilingual.md / stats | 缺译标记+溯源 |
| 8 | `number_engine.py audit --work $W` | → number_audit.json + findings.json | 双向比对：缺失/增译/改动分级/单位差异 |
| 9 | Agent 复核修订 | → 追加修订 → 重跑 7、8 | 删误报/修译文/定性质 |
| 10 | report_builder → assemble_result | → /app/output | 报告、契约 |
| 11 | `make_docx.py --out $O`（v2 核心） | translation_full/bilingual.md → docx（+尽力 PDF） | 纯标准库 OOXML；preview_status 记录降级 |
| 12 | Agent 交付确认 → validate_output → render_previews | preview_status/预览抽查 → 闸门 | docx 结构 zipfile 校验 |

## 关键方法

1. **台账先行**：译前把每个数字（含年份、样本量、温度、百分比、科学计数）登记为
   {raw, value, unit} 三元组，翻译约束与译后核对共用同一台账。
2. **跨语言归一**：万/亿/千/百与 thousand/million/billion 折算为数值比较；
   千分位逗号、×10^n、% / ‰ 归一后等值判定——只允许数学等值的表达转换。
3. **双向比对**：源→译（缺失/改动）与译→源（增译）两方向逐值核对；
   改动按差异量级分三档：末位级=疑似四舍五入/笔误（中）、十倍百倍关系=疑似数字笔误（高）、
   其余=数字被改动（高）。
4. **引用屏蔽**：引用标记（[1]、(Zhang, 2023)）内部数字不纳入数字比对，
   避免把引用编号/年份误当实验数据。

## 适用场景与限制

- 适用：数据密集的实验论文、综述中的统计段落、含 SI 单位与量级词的稿件。
- 限制：中文大写/罗马数字/分数拼写未纳入；数值合理性不属核对范围。

## 失败处理与自查

- 自查：`validate_output.py` PASS；`number_audit.json summary.fidelity` 应为 1.0
  （剩余项均已驳回并附理由）；`stats.coverage`=1.0 否则 partial。
- 常见失败：译文 JSONL 格式错（assemble 计数偏低）；单位写法全角/半角不一致
  （值相等时只报“单位形式差异”低严重度，按第 9 步裁决）。

## 最小示例

见 `examples/minimal_example.md`（合成，标注“示例”）。
