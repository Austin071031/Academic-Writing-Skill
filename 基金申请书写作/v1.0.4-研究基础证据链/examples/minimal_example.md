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
python3 $S/feasibility_engine.py seed --work $W
# …Agent 读 evidence_chain_seed.json 审定取舍、填 relation_to_project，
#   另存 work/evidence_chain.json；写 work/sections/01_立项依据.md 等七节…
python3 $S/draft_builder.py --work $W --out $O
python3 $S/source_audit.py --work $W
python3 $S/elements_check.py --work $W --out $O
python3 $S/feasibility_engine.py audit --work $W
# …Agent 处置 findings，修订后重跑 draft_builder→audit…
python3 $S/report_builder.py --work $W --out $O --focus feasibility --skill "grant-feasibility-evidence v1.0.4"
python3 $S/assemble_result.py --work $W --out $O --skill "grant-feasibility-evidence v1.0.4" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 示意输出（节选，示例标注）

```
[feasibility seed] 证据链行=9（prior_work 文件=2 个） → work/evidence_chain_seed.json
[source_audit] findings=0
[elements_check] covered=7/7
[feasibility audit] findings=0
[validate_output] ALL PASS (8/8)
```

`work/evidence_chain.json` 节选（审定版）：

```json
{"row_id": "R003", "capability": "已获授权发明专利 ZL202210123456.7 一项，涉及界面修饰层配方",
 "evidence_fids": ["F0037", "F0038"],
 "sources": [{"file_id": "F3", "pid": "F3-P005"}],
 "relation_to_project": "配方与涂布工艺保护直接支撑研究内容（二）放大制备的知识产权与工艺复用"}
```

`element_mapping.md` 节选：

| 要素 | 章节 | 段落 | 字数 | 证据数 | 状态 |
|-|-|-|-|-|-|
| 研究基础与可行性 | 07_研究基础与可行性 | 3 | 360 | 10 | ok |
| … | | | | | |

> 本示例全部内容为合成演示，正式案例由平台运行生成。
