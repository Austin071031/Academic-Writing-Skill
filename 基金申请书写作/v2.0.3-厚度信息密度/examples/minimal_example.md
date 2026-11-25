# 最小调用示例（合成演示，非正式案例结果）

## 输入

`/input/`：`case.json`（含 case_id、output_contract）、`task.md`（撰写七要素章节稿）、
`paper.md`（合成原论文）、`prior_work.md`（合成前期成果）。

## 调用

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output; mkdir -p $W $O
python3 $S/init_result.py
python3 $S/inspect_case.py --work $W
python3 $S/parse_materials.py --work $W
python3 $S/fact_ledger.py --work $W
python3 $S/innovation_engine.py seed --work $W
# …Agent 读 innovation_seed.json 审定对比锚点，写 work/sections/01_立项依据.md 等七节…
python3 $S/draft_builder.py --work $W --out $O
python3 $S/source_audit.py --work $W
python3 $S/elements_check.py --work $W --out $O
python3 $S/innovation_engine.py audit --work $W
# …Agent 处置 findings，修订后重跑 draft_builder→audit…
python3 $S/report_builder.py --work $W --out $O --focus innovation --skill "grant-innovation-precision v2.0.3"
python3 $S/assemble_result.py --work $W --out $O --skill "grant-innovation-precision v2.0.3" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 示意输出（节选，示例标注）

```
[innovation seed] 锚点候选=3 gap 上下文=5 → work/innovation_seed.json
[source_audit] findings=0
[elements_check] covered=7/7 thin=0 density_low=0 findings=0
[innovation audit] 条目数=2 findings=0 (clean)
[validate_output] ALL PASS (8/8)
```

注入缺陷（「本研究首次提出…，达到国际领先水平，填补国内外空白」）时：

```
[innovation audit] 条目数=1 findings=10 high=5 medium=5
# banned_modifier×5(high) / no_baseline_anchor / no_difference_statement /
# three_dim_incomplete×3(medium)
```

`element_mapping.md` 节选：

| 要素 | 段落数 | 字数 | 证据数(FID) | 证据密度 | 状态 |
|-|-|-|-|-|-|
| 立项依据 | 5 | 640 | 9 | ok | ok |
| 创新点 | 3 | 320 | 5 | na | ok |
| 技术路线 | 4 | 470 | 6 | ok | ok |
| … | | | | | |

> 本示例全部内容为合成演示，正式案例由平台运行生成。
