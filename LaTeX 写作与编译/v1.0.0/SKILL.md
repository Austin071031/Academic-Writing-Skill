---
name: latex-compile-rescue
description: >-
  LaTeX 编译错误诊断与迭代修复闭环。当任务要求修复/整理 LaTeX 工程使其在指定模板与
  TeX 发行版下编译通过（含定位报错到文件与行号、区分根因与级联错误、交付可继续编辑的
  .tex 源码与编译验证记录）时触发。不适用于：纯文字润色、无 LaTeX 源码的任务、
  需要臆造缺失内容才能完成的任务（此类如实降级并标注）。产物：可编译的 .tex 工程、
  PDF 预览、错误分诊报告、逐条修改记录与 result.json。
---

# latex-compile-rescue：编译得通——错误分诊与迭代修复闭环

你在一个有时间与请求预算的评测沙箱中运行。本 Skill 的目标：**把给定 LaTeX 工程修到
编译通过且交叉引用收敛，交付可继续编辑的源码与可被独立复核的验证记录**。
核心理念：脚本承担全部机械劳动（编译、日志解析、白名单修复），你（Agent）只做判断与改写；
先保底落盘，再迭代求精；每处修改都可回溯到日志证据。

## 0. 触发与不触发

- 触发：/input 含 .tex 工程（或论文 PDF+要求产出 LaTeX 的任务），task.md 要求修复编译
  错误、消除警告、使工程编译通过、整理为可编译投稿稿。
- 不触发：材料中没有任何 LaTeX 源码且任务未要求产出 LaTeX；此时仍按 Phase 0/5 交付
  诚实的 partial 结果并说明原因，不得伪造 .tex。
- 材料只有 PDF 而任务要求"重排为 LaTeX"：先用可用文本抽取工具读 PDF 文本，按论文结构
  重建 .tex 骨架（章节/公式/表格按原文转写），数字与图表引用以 PDF 为唯一事实来源，
  重建不确定处记入 uncertainty。

## 1. 三条红线（违反即失败）

1. **不臆造内容**：不编造作者、单位、数据、文献、DOI；材料缺失的章节/图片/bib 条目，
   只能建 TODO 占位并登记 manual_confirmations，不得补写貌似合理的内容。
2. **不伪造编译结果**：编译结论只能来自真实运行 tex_build.py 的报告；无 TeX 引擎时
   如实记录 exception 并降级 partial，禁止声称"已编译通过"。
3. **机械修复走白名单、语义修复走记录**：safe_fix.py 只做白名单修复；你手工的每处
   语义修改都必须追加到 work/change_log.json（op/file/line/before/after/reason）。

## 2. 运行时契约速览

- 输入：`/input/case.json`、`/input/task.md` 与材料；工作目录 `/app/work`；
  交付目录 `/app/output`，其中必须有含 `case_id` 与 output_contract 全部字段的
  `result.json`。
- 预算：64 次模型请求、900 秒、单次响应 16384 token。**每完成一个 Phase 就把中间
  结果落盘**；任何时候中断，/app/output 里都要有可评的部分结果。
- 本 Skill 全部脚本仅依赖 Python3 标准库，以 `python3 /skills/weekly-skill/scripts/xxx.py`
  调用（下文以 `$S` 代指该目录）。

## 3. 阶段流程

### Phase 0 — 保底与侦察（必做，1 次响应内完成）

```sh
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md \
    --input-dir /input --work /app/work
```

- 读 work/inspection.json：确认 case_id、材料清单、tex_project.main（主文件）、
  engine（引擎猜测）、documentclass、missing_refs（缺失 \input/图片/bib）。
- 材料已暂存到 /app/work/project，**所有修改只改 project/，不改 /input**。
- 精读 /input/task.md（副本在 work/task_copy.md）：把任务要求的改动点逐条抄进
  work/task_items.md（每条一行），这是 Phase 3/4 的核对清单。
- 若无主文件（main 为 null）：在 task_items.md 记录"无 LaTeX 工程"，按第 0 节的
  不触发/降级路径处理，直接跳 Phase 5 交付 partial。

### Phase 1 — 基线编译（建立事实基线）

```sh
python3 $S/tex_build.py --project /app/work/project --work /app/work \
    --tag baseline --until-converge --timeout 120
```

- 读 work/build_report.json：success/converged/各轮错误数/exception。
- 若 exception 为"未找到任何可用 TeX 引擎"：检查环境变量与常见路径一次；仍无则在
  work/exceptions.json 记录 `{"where":"tex_build","error":"无可用TeX引擎"}`，
  转 Phase 2 的源码静态审查（tex_check 不依赖编译），最终 status=partial。
- 若主文件不存在：按 inspection.mains_candidates 人工指定 `--main`。

### Phase 2 — 错误分诊（根因 vs 级联）

```sh
python3 $S/tex_logscan.py --work /app/work --top 15
python3 $S/tex_check.py --work /app/work
```

- 读 work/log_report.json：
  - `first_error` 与 `root_cause_hypothesis` 给出根因假设（缺宏包/缺文件/括号失衡/
    Unicode 引擎错配）；`cascade=true` 的错误是下游症状，**先修根因再复编**，
    不要逐条硬修几十条级联错误。
  - 每条错误带 file:line 与 category（分类体系见 references/error_taxonomy.md）。
- 读 work/source_check.json：悬空 \ref/\cite、缺失 \input、占位符、环境失衡、
  元数据缺项——这些即使编译通过也要按 task.md 处理。
- 修复策略速查（详细判据见 references/fix_playbook.md）：
  - undefined_control_sequence → 先查 likely_package（白名单映射）；
  - missing_file(.sty/.cls) → 模板类文件缺失：查材料目录是否自带，否则记录
    manual_confirmations 并改用可用类（须在 change_log 写明替代理由）；
  - unicode_char_pdflatex 成片 → 引擎错配：用 `--engine xelatex` 复编，不必改源码；
  - math_mode/brace_mismatch → 人工到 file:line 核对补 $ 或 }；
  - undefined_citation → 查 source_check 的 bib 条目，疑似键名笔误则比对近似键
    后改正文或补条目（条目信息必须来自材料，不得编造）。

### Phase 3 — 迭代修复（机械先行，语义随后）

```sh
python3 $S/safe_fix.py --work /app/work --dry-run   # 先看会改什么
python3 $S/safe_fix.py --work /app/work             # 应用白名单修复
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag iter1 --timeout 120
```

- safe_fix.py 只做三类高置信修复并自动记 work/fix_log.json：补缺失宏包
  （命令→宏包白名单，hyperref/cleveref 置于宏包区末尾）、引擎魔法注释、
  缺失 \input 的 TODO 占位文件（同时登记 manual_confirmations）。
- 剩余错误由你按 log_report 的 file:line 逐个编辑源码修复；每处修改追加一条
  change_log（格式见第 6 节）。**改完一批就复编一次**（tag 用 iter2/iter3…），
  用"错误数下降"作为进度信号；同一根因修两轮无效就停下来重读日志，不要反复盲改。
- task_items.md 中任务明确要求的改动点（如"改为三线表""统一公式编号"），在此阶段
  一并完成并记 change_log；材料不足的判断记入 uncertainty.json。
- 预算过半规则见第 5 节。

### Phase 4 — 收敛验证（改得对 + 复现得了）

```sh
python3 $S/tex_build.py --project /app/work/project --work /app/work \
    --tag final --until-converge --timeout 150
python3 $S/tex_check.py --work /app/work
python3 $S/tex_logscan.py --work /app/work --top 20
```

- 验收标准（对照 task_items.md 逐条打勾）：
  1. build_report.final.success=true（PDF 产出且末轮 0 错误）；
  2. converged=true（无 Rerun 提示、无未解析交叉引用）；若为 false 须能在
     uncertainty 中指出具体未定义标签/引用及其原因；
  3. source_check 的 undefined_refs/undefined_cites/placeholders 为 0，或逐一在
     uncertainty/manual_confirmations 中说明；
  4. log_report 无 >20pt 的 overfull hbox（超出版心的行），有则修表格/长公式；
  5. 任务要求的改动点全部完成或显式标注。
- 不达标且预算允许 → 回 Phase 3；预算不足 → 如实 partial。

### Phase 5 — 交付（结构化结果）

先把 Phase 2-4 的判断写成 4 个 JSON（已存在的会被合并，不存在也要建空数组）：

- work/evidence_map.json：`[{"item":"修复项","location":"main.tex:19",
  "source":"build_baseline.log 第3条错误","support":"编译日志/源码行","action":"加载booktabs"}]`
- work/change_log.json：你的全部手工修改（safe_fix 的修复已在 fix_log.json，
  assemble 会自动并入）。
- work/uncertainty.json：`[{"item":"...","reason":"材料未提供/无法判定","impact":"..."}]`
- work/manual_confirmations.json + work/exceptions.json（占位文件、缺模板、无引擎等）。

```sh
python3 $S/assemble_result.py --work /app/work --out /app/output \
    --case /input/case.json --skill "latex-compile-rescue v1.0.0" \
    --status success   # 或 partial / failed，按实际
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

- assemble 会复制可编辑工程到 /app/output/latex_project/（剔除 .aux 等中间文件）、
  最终 PDF 为 preview.pdf、全部报告到 reports/，并保证 result.json 顶层含
  output_contract 全部字段。
- validate 打印 PASS 才算交付完成；FAIL 项逐条补救。
- status 判定：全部验收标准达标=success；核心产物在但有未决项=partial；
  无法产出可编辑工程=failed（必须写清 exceptions）。

## 4. 异常处置表

| 异常 | 识别 | 处置 |
|-|-|-|
| 无 TeX 引擎 | tex_build exception | 记录 exceptions；只做源码静态审查；status≤partial |
| 主文件不明 | inspection.main=null | 按 mains_candidates 人工指定；都不行则降级 partial |
| 缺宏包(.sty) | missing_file | 查材料目录自带文件；没有则用功能等价宏包替代并记 change_log+uncertainty |
| 缺模板类(.cls) | missing_file | 同上；无替代则用 ctexart/article 兜底并在 uncertainty 说明版式不保真 |
| 缺图片 | inspection missing_refs graphics | 保留 \includegraphics 并记 manual_confirmations；不为凑编译删图引用 |
| 缺 .bib/条目 | undefined_citation | 键名近似匹配修正；条目信息只能来自材料；缺条目记 manual_confirmations |
| Unicode 成片报错 | root_cause 提示引擎错配 | 切 xelatex/lualatex 复编；或按任务要求补 ctex 宏包 |
| 编译超时挂起 | pass timed_out | 查死循环（如 \input 自包含、未闭合环境）；定位后修复并记 change_log |
| 报错超 50 条 | log_report summary | 只修根因与首批非级联错误，复编后再看残余 |
| 预算告急 | 请求数>40 或时间>600s | 立即跳 Phase 4/5，以当前最好状态交付 partial |

## 5. 预算兜底

- 模型请求 ≤64：Phase 0-1 用 ≤6 次；Phase 2-3 每轮"修一批+复编"控制在 2-3 次；
  Phase 4-5 预留 ≥6 次。**请求数过半（>32）仍未编译通过**：停止进一步修复，
  把当前最好状态跑 Phase 4-5，status=partial 并写明剩余错误清单。
- 单次响应 16384 token：读日志/报告用脚本摘要（--top），不要整文件贴入上下文；
  大文件编辑用行号定位的精确替换，不重写全文。

## 6. work/ 中间文件格式

- change_log.json：`[{"op":"edit|add_package|stub|delete","file":"main.tex","line":19,
  "before":"\\toprule（未加载booktabs）","after":"\\usepackage{booktabs}",
  "reason":"...","evidence":"build_baseline.log"}]`
- stats.json：`{"baseline_errors":N,"final_errors":M,"fix_rounds":K,"task_items_done":"x/y"}`
- fix_log.json 由 safe_fix.py 维护，不要手改；你自己的修改只写 change_log.json。

## 7. 参考文件（按需取读，不要全读）

- references/error_taxonomy.md — 错误分类体系与各类首选修法
- references/fix_playbook.md — 高频错误的逐步修复剧本（含 worked example）
- references/failure_modes.md — 已知失败模式与规避
- examples/minimal_example.md — 合成案例的完整调用示例（非正式案例结果）
