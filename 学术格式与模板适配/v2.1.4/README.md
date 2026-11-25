# 学术格式与模板适配 · v2.1.4

基于 **v2.0.0**（attempt 101404，得分 58.6667，本题首个有效出分基线）的单方向增量版。
本版唯一主线：**文题块保护**——`adapt_docx.restyle_body` 对首个结构化块
（标题/前置部分标记/题注）之前的段落（文题、作者、单位）跳过正文 run 归一化，
保留作者原字号/字体/加粗，保护段落数登记 changelog。输出契约键名/结构零改动。

## 丢分根因

正文 run 归一化此前对**所有**正文类段落生效：文题（如 16pt 黑体加粗居中）与作者行
会被一并刷成正文规格（12pt），渲染成品中文题与正文同字号——这是"格式被错误改动"
的典型，直接落在结果正确性(15)/结果完整性(5) 的扣分面上，且渲染预览中一眼可见。

## 与父辈差异（评分对照）

| 改动 | 归属评分维度 | p1 实测证据 |
|-|-|-|
| 文题块段落豁免正文 run 归一化 | 实际效果(40)：结果正确性15/结果完整性5 | 文题保留 16pt 黑体加粗（父辈被压成 12pt 正文规格），保护 2 段登记 changelog；正文段落归一化行为不变，fidelity PASS |

## 回归

p1 九阶段全 success、compliance 12 PASS/0 FAIL/0 WARN/3 SKIP 与父辈逐项持平、
fidelity PASS（不动任何文本）、契约键与填充 3/3 一致；p2 success；p3 诚实 failed。

## 调用（与父辈一致）

```bash
python3 /skills/weekly-skill/scripts/run_pipeline.py \
    --case /input/case.json --task /input/task.md \
    --work /app/work --outdir /app/output
```
