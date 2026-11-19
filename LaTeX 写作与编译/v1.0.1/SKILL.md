---
name: latex-math-consistency
description: >-
  LaTeX 数学公式一致性与排版合规审查修复。当任务涉及公式改写/校对、公式编号与引用整理、
  多行公式对齐、符号与单位正斜体规范、定理环境整理，或要求修复后的工程在指定模板下
  编译通过且公式与正文叙述一致时触发。不适用于：纯文字润色、无 LaTeX 源码且不要求
  产出 LaTeX 的任务。产物：公式审查报告、逐条留痕的修改、可编译工程与 PDF 预览、
  结构化 result.json。
---

# latex-math-consistency：改得对——公式专项审查与一致性修复

核心理念：脚本先普查全部公式环境并给出带 file:line 的发现清单（只诊断不擅改），
你（Agent）对照任务要求与材料原文做语义判断；每处公式修改都能回溯到审查证据；
最终用多轮编译 + 静态复核双通道验证"改得对"。

## 0. 触发与不触发

- 触发：/input 含 .tex 工程且任务涉及公式（新增/改写/编号/对齐/单位规范/定理环境）；
  或编译错误集中在数学模式（Missing $、Undefined control sequence 于公式内）。
- 不触发：材料无任何 LaTeX 源且任务不要求 LaTeX 产物 → 按 Phase 0/5 交付诚实 partial。
- 材料为论文 PDF + 要求重排公式：以 PDF 为公式内容的唯一事实来源，逐式转写，
  看不清的符号记 uncertainty，禁止猜测补全。

## 1. 三条红线

1. **不改公式含义**：编号、对齐、正斜体、环境替换（eqnarray→align）都只改排版不改
   数学内容；任何影响含义的改动必须有 task.md 或材料依据并记 change_log。
2. **不臆造符号与数值**：符号定义、上下标、数值以材料为准；材料模糊处记 uncertainty。
3. **不留未验证修改**：每批改完必须复编；math_audit 的 warn 级发现须逐条处置
   （修复或在 uncertainty 说明不处理的理由）。

## 2. 运行时契约速览

- 输入 /input/case.json + task.md + 材料；工作 /app/work；交付 /app/output
  （result.json 含 case_id + output_contract 全部字段）。
- 预算 64 请求 / 900 秒 / 16384 token；脚本（$S=/skills/weekly-skill/scripts）承担
  普查与编译，你只做判断与精确编辑。

## 3. 阶段流程

### Phase 0 — 保底与侦察（同通用流程）

```sh
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md \
    --input-dir /input --work /app/work
```

精读 task.md（副本 work/task_copy.md），把公式相关的任务要求逐条抄入
work/task_items.md（如"所有被引用公式须编号""单位用 siunitx""改为 align 环境"）。

### Phase 1 — 基线编译 + 公式普查

```sh
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
python3 $S/tex_logscan.py --work /app/work --top 10
python3 $S/math_audit.py --work /app/work
python3 $S/tex_check.py --work /app/work
```

- 若编译失败：先按 tex_logscan 的根因假设修编译（数学模式错误用 M 类判据，其余见
  references/failure_modes.md），编译通过后再做公式合规审查。
- 读 work/math_report.json：
  - env_counts：公式环境统计（equation/align/equation* 比例），对照任务对编号的要求；
  - findings：M1 $$ 显示数学、M2 eqnarray、M3 编号/引用问题、M4 斜体文字下标、
    M5 数学中斜体单位、M6 裸算子、M7 \left/\right 不配对；每条含 file:line 与建议。
- 读 work/source_check.json：undefined_refs 中的公式 \eqref 悬空、重复 label。

### Phase 2 — 一致性核对（公式 vs 正文叙述）

- 对每个带编号公式：在正文找到其 \eqref 引用处，核对编号叙述（"式(3)"与实际编号）
  与符号用法是否一致；发现"正文说式(3)实为式(4)"记 finding 并修正引用键。
- 符号表核对：同一符号在材料中含义唯一；发现同符异义/异符同义且任务要求统一时，
  按材料中占优用法统一，记 change_log 与 uncertainty（影响面）。
- 数值核对：公式中的数值常数与材料/正文一致；不一致且材料有明确值时修正并记
  change_log（evidence 指向材料位置），材料不明确时记 uncertainty，不得擅改。

### Phase 3 — 修复（判断在你，留痕在案）

按 math_report findings 分批修复，每批 ≤5 处，改完即复编：

```sh
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag iter1 --timeout 120
python3 $S/math_audit.py --work /app/work   # 复扫确认 findings 下降
```

修复判据（详见 references/math_rules.md）：
- M1：`$$...$$` → `\[...\]`（注意跨行 $$ 的配对）。
- M2：eqnarray → align，对齐点 `&=&` → `&=`，删除多余 `&`；复编核对渲染。
- M3a：任务要求"仅被引用公式编号" → 未被引用公式改 * 环境或 \notag；
  任务要求"全编号" → 反向处理。
- M4：`x_{max}` → `x_{\mathrm{max}}`（文字下标正体）；变量下标（i, j, k）保持斜体。
- M5：`$10 m/s$` → `\qty{10}{\m\per\s}`（siunitx v3）或 `\SI{10}{\meter\per\second}`；
  先确认工程已加载 siunitx，未加载则补（记 change_log）。
- M6：`sin(x)` → `\sin(x)`；自定义算子用 `\operatorname{...}`。
- M7：跨行 \left/\right 用 `\right.`/`\left.` 占位配对。

### Phase 4 — 双通道验证

```sh
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag final --until-converge --timeout 150
python3 $S/math_audit.py --work /app/work
python3 $S/tex_check.py --work /app/work
```

验收：final.success=true 且 converged=true（或逐项说明）；math_report 的 warn 级
findings 清零或逐条登记；source_check 的 undefined_refs/placeholders 清零或登记；
task_items.md 逐条打勾。

### Phase 5 — 交付

写 work/evidence_map.json（每条修复←→math_report finding/材料位置）、change_log.json、
uncertainty.json、manual_confirmations.json、exceptions.json、stats.json 后：

```sh
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-math-consistency v1.0.1" --status success   # 或 partial
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

## 4. 异常处置表

| 异常 | 处置 |
|-|-|-|
| 无 TeX 引擎 | 记 exceptions；仅静态审查交付，status≤partial |
| 公式含义看不清（PDF 转写） | 记 uncertainty（哪个符号、何处置疑）；不猜 |
| 任务与模板冲突（如编号要求 vs 类默认） | 以 task.md 为准，记 uncertainty 说明取舍 |
| siunitx 版本差异（\SI vs \qty） | 按编译结果选可用命令；v2 语法报错则退回 v3 前语法并注明 |
| 公式跨页溢出 | 长式拆 multline/split；overfull>20pt 必须处理 |
| 定理环境未定义 | 检查 amsthm 与 \newtheorem 定义；缺则补定义（格式仿已有定理） |
| 预算告急（请求>32） | 停止修复，以当前状态走 Phase 4/5 交付 partial |

## 5. 预算兜底

Phase 0-1 ≤8 请求；修复按"批"推进，每批 2 请求（改+复编）；Phase 4-5 预留 ≥6。
math_audit 可反复运行（幂等），用 findings 数下降作为进度信号；两轮无下降即停，
把剩余 findings 写入 uncertainty 交付。

## 6. work/ 中间文件格式

- change_log.json：`[{"op":"math_edit","file":"sec2.tex","line":41,
  "before":"$$E=mc^2$$","after":"\\[E=mc^2\\]","reason":"M1 显示数学规范",
  "evidence":"math_report.json#M1"}]`
- stats.json：`{"findings_initial":N,"findings_final":M,"task_items_done":"x/y",
  "env_counts":{...}}`

## 7. 参考文件（按需取读）

- references/math_rules.md — M1-M7 判据与正误对照示例
- references/failure_modes.md — 已知失败模式
- examples/minimal_example.md — 合成示例（非正式案例结果）
