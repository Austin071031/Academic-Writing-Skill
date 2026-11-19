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
python3 $S/alignment_engine.py seed --work $W      # 写作前：打印条目设计指引
# …Agent 设计 3 目标-3 内容-3 路线-3 指标，写 work/sections/NN_要素名.md…
python3 $S/draft_builder.py --work $W --out $O
python3 $S/alignment_engine.py seed --work $W      # 落稿后：打印四节条目计数自查
python3 $S/source_audit.py --work $W
python3 $S/elements_check.py --work $W --out $O
python3 $S/alignment_engine.py audit --work $W --out $O
# …Agent 处置 findings，修订后重跑 draft_builder→audit…
python3 $S/report_builder.py --work $W --out $O --focus alignment --skill "grant-alignment-matrix v1.0.2"
python3 $S/assemble_result.py --work $W --out $O --skill "grant-alignment-matrix v1.0.2" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 示意输出（节选，示例标注）

```
[alignment seed] 目标=3 内容=3 路线=3 指标=3 → work/alignment_seed.json
[source_audit] findings=0
[elements_check] covered=7/7
[alignment audit] 目标=3 内容=3 路线=3 指标=3 matches=16 findings=0 (clean)
[validate_output] ALL PASS (8/8)
```

负例（目标三条、路线两条、缺考核指标节，合成注入缺陷）：

```
[alignment audit] 目标=3 内容=2 路线=2 指标=0 matches=1 findings=3 high=2 medium=1
# high count_mismatch：目标 3 条、内容 2 条，数量不一致（应一一对应）
# high missing_section：草稿中未找到「考核指标」章节
# medium orphan_goal：研究目标「目标三」无任何对应研究内容条目
```

`alignment_table.md` 节选：

| 研究目标 | 对应研究内容 | 对应技术路线 | 对应考核指标 |
|-|-|-|-|
| 目标一 阐明偶极取向调控能级排列机制… | （一） 偶极取向调控能级排列机制研究… | 步骤一 针对研究内容（一）… | 指标一 对应目标一… |
| 目标二 揭示钝化基团与缺陷位点作用机制… | （二） 钝化基团与界面缺陷位点作用机制研究… | 步骤二 针对研究内容（二）… | 指标二 对应目标二… |

> 本示例全部内容为合成演示，正式案例由平台运行生成。
