---
name: latex-table-governance
description: >-
  LaTeX 表格与浮动体治理：列数一致性、三线表改造、宽表跨页与列宽、缩放掩盖清除、
  图表标题与浮动位置规范。当任务要求修复/改造表格、消除表格编译错误与超宽溢出、
  统一图表题注与引用、或使含复杂表格的工程在指定模板下编译通过时触发。不适用于：
  无 LaTeX 源码且不要求 LaTeX 产物的任务。产物：表格审查报告、机械+语义双重留痕的
  修改、可编译工程与 PDF 预览、结构化 result.json。
---

# latex-table-governance：改得对——表格与浮动体治理

核心理念：表格问题有高度机械性（列数、线型、浮动位置），适合脚本普查与受限自动修复；
但"改数值、改列结构"永远由你（Agent）对照材料判断。题面明确反对**溢出裁切**和
**靠缩放掩盖**——\resizebox 包表是 finding，不是解药。

## 0. 触发与不触发

- 触发：任务涉及表格修复/改造/三线表化/宽表处理/图表题注与浮动整理；
  或编译错误指向 tabular（Extra alignment tab、Misplaced \noalign、overfull 源于表）。
- 不触发：材料无 LaTeX 源且不要求 LaTeX 产物 → 按 Phase 0/5 交付诚实 partial。

## 1. 三条红线

1. **不改表格数据**：数值、行列含义以材料为唯一来源；只改排版结构，数据改动必须有
   task.md 依据并记 change_log（evidence 指向材料）。
2. **不用缩放/裁切掩盖超宽**：禁止 \resizebox/\scalebox 包表、禁止 \small 之外再叠
   字号缩水来假装不宽；超宽表走 tabularx/longtable/列宽重分配。
3. **机械修复只走白名单**：table_audit --apply 只做 hline→booktabs（简单模式）与
   浮动位置放宽；其余一律 Agent 手工改并记 change_log。

## 2. 运行时契约速览

输入 /input/case.json + task.md + 材料；工作 /app/work；交付 /app/output
（result.json 含 case_id + output_contract 全部字段）。预算 64 请求/900 秒。
$S=/skills/weekly-skill/scripts，全部脚本纯标准库。

## 3. 阶段流程

### Phase 0 — 保底与侦察

```sh
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md \
    --input-dir /input --work /app/work
```

把 task.md 的表格相关要求抄成 work/task_items.md（如"全部三线表""表 3 跨页处理"
"题注在表上方"）。

### Phase 1 — 基线编译 + 表格普查

```sh
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
python3 $S/tex_logscan.py --work /app/work --top 10
python3 $S/table_audit.py --work /app/work
python3 $S/tex_check.py --work /app/work
```

- 编译先修通（表格相关编译错见 references/table_rules.md 的 T3/T4 判据）。
- 读 work/table_report.json：tables[] 逐表体检（caption/label/列数/booktabs/缩放包裹/
  行数），findings 带 file:line：
  T1 缺 caption/label；T2 caption 位置；T3 行列数不一致（error 级）；
  T4 仅 \hline；T5 resizebox 包裹（warn）；T6 浮动位置 [h]/[H]；
  T7/T8 超宽/跨页嫌疑（启发式，标注为估计）。

### Phase 2 — 机械修复（受限）

```sh
python3 $S/table_audit.py --work /app/work --apply-booktabs --apply-float-htbp
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag iter1 --timeout 120
```

- --apply-booktabs 仅转换"独立成行的 \hline ≤4 条"的简单模式，自动记 fix_log；
  复杂模式（\cline、\hline 混排、竖线）由你手工按 references/table_rules.md 改造。
- 转换后若报 \toprule 未定义：补 `\usepackage{booktabs}`（记 change_log）。
- --apply-float-htbp 把 [h]/[H] 放宽为 [htbp]，防 "Too many unprocessed floats"。

### Phase 3 — 语义修复（逐表处置）

按 findings 逐表处理，每表改完复编一次：

- T3 列数不一致：数 & 与列声明；\multicolumn 按展开列数计；定位行修正。
- T5 缩放掩盖：拆 \resizebox，按超宽原因分流——列内容长 → tabularx 的 X 列自动换行；
  列数多 → 减列/转置/拆两表；跨页 → longtable（重复表头 \endhead）；字号只允许
  \small/\footnotesize 一档，且记 change_log 说明。
- T7/T8 启发式超宽/跨页：目视 preview.pdf 对应页确认后再动手；估计不实可记
  uncertainty 不处理。
- caption/label：缺则补（label 命名沿用工程既有风格 tab:xxx）；caption 位置按
  task.md/模板要求统一；正文 \ref 指向补全。
- 数值核对：表内数值与材料/正文一致；不一致且材料明确时修正（记 change_log），
  材料不明确时记 uncertainty，不得擅改。

### Phase 4 — 验证

```sh
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag final --until-converge --timeout 150
python3 $S/table_audit.py --work /app/work
python3 $S/tex_check.py --work /app/work
python3 $S/tex_logscan.py --work /app/work --top 20
```

验收：final.success=true 且 converged=true（或逐项说明）；table_report 的 error 级
清零、warn 级清零或登记；log_report 无 >20pt overfull（表格是 overfull 重灾区）；
tex_check 的 undefined_refs（tab: 类）清零；task_items.md 打勾。

### Phase 5 — 交付

写 work/evidence_map.json（每表处置←→finding/材料）、change_log.json、
uncertainty.json、manual_confirmations.json、exceptions.json、stats.json：

```sh
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-table-governance v1.0.2" --status success   # 或 partial
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

## 4. 异常处置表

| 异常 | 处置 |
|-|-|-|
| 无 TeX 引擎 | 记 exceptions；静态审查交付，status≤partial |
| booktabs 不可用 | 退回 \hline 但保留其他修复；记 uncertainty |
| 表格数据与材料冲突 | 以材料为准修正并记 change_log；双方都不明记 uncertainty |
| 超宽表无优雅解 | 给 longtable/横向表（sidewaystable 需 rotating）两案，按模板选并注明 |
| \cline 复杂表头 | 不机械转换；手工 booktabs 化用 \cmidrule(lr){i-j} |
| 图片缺失 | 保留 \includegraphics，记 manual_confirmations；不删图 |
| 浮动体堆积 | [h]→[htbp] 已机械处理；仍堆积检查 \clearpage 需求，记 change_log |
| 预算告急（请求>32） | 停止修复，当前状态走 Phase 4/5 交付 partial |

## 5. 预算兜底

Phase 0-2 ≤10 请求（机械修复覆盖大部分工程）；Phase 3 每表 2 请求（改+复编）；
Phase 4-5 预留 ≥6。table_audit 幂等可复扫，findings 数下降为进度信号。

## 6. work/ 中间文件格式

- change_log.json：`[{"op":"table_edit","file":"results.tex","line":33,
  "before":"\\resizebox{\\textwidth}{!}{\\begin{tabular}...",
  "after":"\\begin{tabularx}{\\textwidth}{lX}...","reason":"T5 清除缩放掩盖",
  "evidence":"table_report.json#T5"}]`
- fix_log.json 由 table_audit --apply 维护，不要手改。
- stats.json：`{"tables":N,"findings_initial":X,"findings_final":Y,"applied_fixes":Z}`

## 7. 参考文件（按需取读）

- references/table_rules.md — T1-T8 判据与改造范式（tabularx/longtable/三线表）
- references/failure_modes.md — 已知失败模式
- examples/minimal_example.md — 合成示例（非正式案例结果）
