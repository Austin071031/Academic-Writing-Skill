# 学术格式与模板适配 · v2.1.2

基于 **v2.0.0**（attempt 101404，得分 58.6667，本题首个有效出分基线）的单方向增量版。
本版唯一主线：**修复字体嵌入核验的误判**——`render_preview.pdf_fonts` 改为从行尾
右对齐解析 pdffonts 的 emb/sub 标志。输出契约键名/结构零改动。

## 丢分根因

pdffonts 输出的 type/encoding 列可含空格（`Type 1`、`CID Type 0`、`Identity-H`），
父辈按左对齐下标取第 4 列，对多词类型行读到的是 `Builtin` 等词而非 emb 标志，
于是把**实际已嵌入**的字体报告为未嵌入。中文学术稿件几乎必然命中（CJK 字体即
`Type 1`/`CID Type 0` 行），导致 `render_report.json` 的 `all_fonts_embedded=false`
——导出的 PDF 本身合规，但核验证据自称不合规，直接影响"交得出"维度的判定。

## 与父辈差异（评分对照）

| 改动 | 归属评分维度 | p1 实测证据 |
|-|-|-|
| emb/sub 标志右对齐解析（行尾 5/4 位） | 实际效果(40)：结果正确性15/结果可核验性5；可靠体验(10) | `all_fonts_embedded`：false → **true**（pdffonts 实读 5/5 字体 emb=yes，与真相一致） |

## 回归

p1 九阶段全 success、compliance 12 PASS/0 FAIL/0 WARN/3 SKIP 与父辈逐项持平、
fidelity PASS、契约键与填充 3/3 一致；p2 success；p3 诚实 failed。

## 调用（与父辈一致）

```bash
python3 /skills/weekly-skill/scripts/run_pipeline.py \
    --case /input/case.json --task /input/task.md \
    --work /app/work --outdir /app/output
```
