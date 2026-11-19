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
python3 $S/question_engine.py seed --work $W
# …Agent 读 question_seed.json 审定候选，写 work/sections/02_科学问题.md 等七节…
python3 $S/draft_builder.py --work $W --out $O
python3 $S/source_audit.py --work $W
python3 $S/elements_check.py --work $W --out $O
python3 $S/question_engine.py audit --work $W
# …Agent 处置 findings，修订后重跑 draft_builder→audit…
python3 $S/report_builder.py --work $W --out $O --focus question --skill "grant-question-convergence v1.0.1"
python3 $S/assemble_result.py --work $W --out $O --skill "grant-question-convergence v1.0.1" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 示意输出（节选，示例标注）

```
[question seed] 问题候选=3 宽泛表述警示=0 → work/question_seed.json
[source_audit] findings=0
[elements_check] covered=7/7
[question audit] findings=0
[validate_output] ALL PASS (8/8)
```

`work/sections/02_科学问题.md`（通过审计的写法）节选：

```markdown
# 科学问题

本课题聚焦一个核心科学问题：两性离子界面修饰层如何通过偶极取向与缺陷钝化的
协同作用抑制钙钛矿/传输层界面的非辐射复合？该问题可分解为两个子问题：
其一，偶极取向对能级排列的定量贡献尚不清楚〔F0018〕；
其二，钝化基团与缺陷位点的作用机制亟待阐明。
研究边界限定于界面工程，不涉及器件封装工艺的系统性研究。
```

审计命中行示例：`[question audit] findings=3 medium=2 high=1`（问题过多/无分解/过大表述）。

> 本示例全部内容为合成演示，正式案例由平台运行生成。
