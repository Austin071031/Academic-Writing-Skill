# 学术格式与模板适配 · v2.1.0

基于 **v2.0.0**（attempt 101404，得分 58.6667，本题首个有效出分基线）的单方向增量版。
本版唯一主线：**把模板实测样式接通到适配层**——`extract_spec` 新增
`project_measured_styles`，将 measure_template 实测的 Normal/标题/题注/参考文献样式
（字号、字体、行距、首行缩进）映射进 `spec` 的 body/headings/captions/references 规格组；
任务文本仍然优先（deep_merge 冲突登记不变）。输出契约键名/结构零改动。

## 丢分根因（父辈实跑证据）

模板为 docx 且任务文本未写明正文规格时，实测值到不了适配层：v2.0.0 在代理用例 p1 上
`spec.body = {}`，正文被强制套内置默认 12pt/Times New Roman——模板真实要求是 10.5pt。
即"认得准"的实测成果没有进入"排得对"，与赛题"只改了几处看得见的格式"的反面判据直接相关。

## 与父辈差异（评分对照）

| 改动 | 归属评分维度 | p1 实测证据 |
|-|-|-|
| 实测样式→规格组映射（仅补缺失键，文本优先） | 实际效果(40)：任务完成度15/结果正确性15 | `spec.body`：{} → {10.5pt, TNR/宋体, 1.5倍行距, 首行缩进2字符} |
| compliance 正文 run 抽查限定正文段落（标题/题注/参考文献/目录 run 不计入） | 结果可核验性5（消除映射激活后的误报 WARN） | compliance：12 PASS/0 FAIL/0 WARN/3 SKIP → **23 PASS/0 FAIL/0 WARN/2 SKIP** |

## 回归

p1 九阶段全 success、fidelity PASS、result.json 契约键/uncertainty 子键/contract 字段
与父辈逐项一致、契约填充 3/3；p2（劣化 case.json）success；p3（空输入）诚实 failed。
父辈全绿指标零变红。

## 调用（与父辈一致）

```bash
python3 /skills/weekly-skill/scripts/run_pipeline.py \
    --case /input/case.json --task /input/task.md \
    --work /app/work --outdir /app/output
```
