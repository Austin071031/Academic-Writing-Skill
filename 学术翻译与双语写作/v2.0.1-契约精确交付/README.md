# contract-exact-delivery v2.0.1

学术翻译 Skill（v2 迭代·契约精确交付方向，父辈 v1.0.1）：result.json 逐字段
语义化填充（文件+sha256+摘要+预览），内置数据字段保护，override 人工映射通道，
未映射字段如实置 null。保留父辈数字台账与双向比对。

## 安装

自包含 Skill；平台安装为 `/skills/weekly-skill` 后按 `SKILL.md` 执行。
本地复现仅需 Python 3.8+ 标准库（PDF 可选 `pdftotext`）。

## 快速开始

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output; mkdir -p $W $O
python3 $S/init_result.py && python3 $S/inspect_case.py --work $W
python3 $S/parse_manuscript.py --work $W && python3 $S/segment_builder.py --work $W
python3 $S/number_engine.py ledger --work $W
# Agent 翻译 → translations.jsonl
python3 $S/assemble_translation.py --work $W --out $O
python3 $S/number_engine.py audit --work $W
python3 $S/report_builder.py --work $W --out $O --focus numbers --skill "contract-exact-delivery v2.0.1"
python3 $S/assemble_result.py --work $W --out $O --skill "contract-exact-delivery v2.0.1" --status success
python3 $S/contract_fill.py --work $W --out $O   # 本版核心：逐字段语义化填充
# Agent 复核 contract_fill 报告，必要时写 contract_override.json 重跑
python3 $S/validate_output.py --out $O --work $W && python3 $S/render_previews.py --out $O
```

## 输入 / 输出

- 输入：`/input/case.json`（含 output_contract）、`/input/task.md`、稿件。
- 输出：译文与机检产物 + 逐字段填充的 `result.json`（含 contract_fill 映射报告）。

## 边界

- 关键词匹配为启发式，Agent 复核步骤不可跳过；契约要求内联长文时以 file 引用为准。

## 仓库与维护

- GitHub：<https://github.com/Austin071031/Academic-Writing-Skill>（`学术翻译与双语写作/v2.0.1-契约精确交付/`）
- 变更历史见 `CHANGELOG.md`（含 v1.0.1 评分基线）。
