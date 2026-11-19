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
python3 $S/rationale_engine.py seed --work $W
# …Agent 读 rationale_chain.json 审定槽位，写 work/sections/01_立项依据.md 等七节…
python3 $S/draft_builder.py --work $W --out $O
python3 $S/source_audit.py --work $W
python3 $S/elements_check.py --work $W --out $O
python3 $S/rationale_engine.py audit --work $W
# …Agent 处置 findings，修订后重跑 draft_builder→audit…
python3 $S/report_builder.py --work $W --out $O --focus rationale --skill "grant-rationale-chain v1.0.0"
python3 $S/assemble_result.py --work $W --out $O --skill "grant-rationale-chain v1.0.0" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 示意输出（节选，示例标注）

```
[rationale seed] 现状候选=23 瓶颈候选=5 我们候选=17 → work/rationale_chain.json
[source_audit] findings=0
[elements_check] covered=7/7
[rationale audit] findings=0
[validate_output] ALL PASS (8/8)
```

`element_mapping.md` 节选：

| 要素 | 章节 | 段落 | 字数 | 证据数 | 状态 |
|-|-|-|-|-|-|
| 立项依据 | 01_立项依据 | 4 | 520 | 9 | ok |
| 科学问题 | 02_科学问题 | 2 | 210 | 3 | ok |
| … | | | | | |

> 本示例全部内容为合成演示，正式案例由平台运行生成。
