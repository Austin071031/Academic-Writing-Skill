# 最小调用示例（合成演示，非正式案例结果）

## 输入

`/input/`：`case.json`（含 case_id、output_contract）、`task.md`（撰写七要素章节稿）、
`paper.md`（合成原论文）、`prior_work.md`（合成前期成果）。

## 调用（v2.0.0 快速主通道，8 步）

```bash
S=/skills/weekly-skill/scripts; W=/app/work; O=/app/output; mkdir -p $W $O
python3 $S/init_result.py
python3 $S/inspect_case.py --work $W
python3 $S/parse_materials.py --work $W
python3 $S/fact_ledger.py --work $W
python3 $S/sections_scaffold.py --work $W        # 生成七节骨架 + FID 候选清单（幂等）
python3 $S/innovation_engine.py seed --work $W
# …Agent 读 materials_digest.md + innovation_seed.json + 骨架候选清单，
#  直接在 work/sections/01_立项依据.md 等骨架上一轮写完七节…
python3 $S/draft_builder.py --work $W --out $O
python3 $S/source_audit.py --work $W
python3 $S/elements_check.py --work $W --out $O
python3 $S/innovation_engine.py audit --work $W
# …Agent 当轮处置 high 级 findings，修订后重跑本步四脚本；
#  第二轮复核仅剩余预算>15 才做…
python3 $S/report_builder.py --work $W --out $O --focus innovation --skill "grant-innovation-precision v2.0.0"
python3 $S/assemble_result.py --work $W --out $O --skill "grant-innovation-precision v2.0.0" --status success
python3 $S/validate_output.py --out $O --work $W
python3 $S/render_previews.py --out $O --work $W
```

## 骨架示意（sections_scaffold.py 生成）

```markdown
# 立项依据

<!-- sections_scaffold 骨架：整文件可覆写为成稿；本要素字数目标 ≥600 字 -->
<!-- 候选事实（fact_ledger.json，按要素关键词+role_guess 匹配，≤12 条）： -->
<!--   F0005 | number | 23.4 | % | 来源 F2-P003 -->
<!--   F0019 | citation | [2,3] | - | 来源 F2-P005 -->

【在此撰写：立项依据 正文，≥600 字；材料事实句末标〔Fxxxx〕，拟开展内容标〔拟〕…】
```

幂等：重跑 scaffold 时，凡文件已含〔Fxxxx〕标记（Agent 已写）即跳过不覆盖。

## 示意输出（节选，示例标注）

```
[scaffold] done: 生成/刷新=7 保留=0 → work/sections
[innovation seed] 锚点候选=3 gap 上下文=5 → work/innovation_seed.json
[source_audit] findings=0
[elements_check] covered=7/7
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

| 要素 | 章节 | 段落 | 字数 | 证据数 | 状态 |
|-|-|-|-|-|-|
| 立项依据 | 01_立项依据 | 4 | 520 | 9 | ok |
| 创新点 | 05_创新点 | 2 | 300 | 5 | ok |
| … | | | | | |

> 本示例全部内容为合成演示，正式案例由平台运行生成。
