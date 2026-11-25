# 学术格式与模板适配 · v2.1.1

基于 **v2.0.0**（attempt 101404，得分 58.6667，本题首个有效出分基线）的单方向增量版。
本版唯一主线：**清除正文段落的行距直改，使样式绑定的行距真实渲染**。
`adapt_docx.restyle_body` 对正文段落删除 `w:spacing` 的 `w:line`/`w:lineRule` 直改属性
（段前段后保留；带编号、分节符、含图/公式段落跳过），每处清除逐条登记 changelog。
输出契约键名/结构零改动。

## 丢分根因

真实稿件普遍带段落级行距直改。OOXML 中段落直改优先级高于样式：即使 Normal 样式
已绑定模板要求的行距，渲染时仍按段落直改显示——"样式已绑定但渲染不合规"，专项检查
只核样式层因而不可见，属于结果正确性的隐性丢分。

## 与父辈差异（评分对照）

| 改动 | 归属评分维度 | p1 实测证据 |
|-|-|-|
| 正文段落行距直改清除（守卫结构性段落） | 实际效果(40)：结果正确性15 | 5 处 `line=240`（单倍）直改全部清除并登记，适配后 document.xml 残留 `w:line` = 0，渲染行距 = 样式绑定值（1.5 倍） |

## 回归

p1 九阶段全 success、compliance 12 PASS/0 FAIL/0 WARN/3 SKIP 与父辈逐项持平、
fidelity PASS（不动任何文本）、契约键与填充 3/3 一致；p2 success；p3 诚实 failed。

## 调用（与父辈一致）

```bash
python3 /skills/weekly-skill/scripts/run_pipeline.py \
    --case /input/case.json --task /input/task.md \
    --work /app/work --outdir /app/output
```
