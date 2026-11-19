---
name: latex-citation-convergence
description: >-
  LaTeX 引用与参考文献收敛：\cite 键解析、bib 条目补全与去重、参考文献样式一致、
  bibtex/biber 链路修复、多轮编译交叉引用收敛。当任务要求修复未定义引用、整理
  参考文献表、合并重复条目、统一引用样式，或使含参考文献的工程编译通过且引用
  全部解析时触发。不适用于：无 LaTeX 源码且不要求 LaTeX 产物的任务。产物：
  引用审查报告、逐条留痕的修改、收敛的可编译工程与 PDF 预览、结构化 result.json。
---

# latex-citation-convergence：引用与参考文献收敛

核心理念：引用问题的本质是"键—条目—样式—编译轮次"四个环节的对齐。脚本把四个环节
全部机读化：键解析（谁悬空）、条目体检（谁缺字段、谁重复）、样式一致性（natbib/
biblatex/样式文件）、收敛驱动（自动多轮编译直至无 Rerun）。你（Agent）只做需要
判断的决策：近似键确认、重复条目合并、缺失条目的材料内补全。

## 0. 触发与不触发

- 触发：任务涉及参考文献/引用修复、bib 整理、引用样式统一；或编译警告含
  Citation undefined / There were undefined references / 参考文献表为空。
- 不触发：材料无 LaTeX 源且不要求 LaTeX 产物 → 按 Phase 0/5 交付诚实 partial。

## 1. 三条红线

1. **不臆造文献与字段**：条目信息（作者/题名/年份/出处/DOI）只能来自材料
   （工程自带 bib、论文 PDF 的参考文献表、任务提供的数据）；查不到的字段留空，
   禁止编造 DOI/卷期页。
2. **合并去重必须可解释**：重复条目合并须在 change_log 写明依据（标题相似度、
   作者、年份比对）并保留被删键→保留键的映射；不得静默删除。
3. **收敛状态如实报告**：converged 由日志判定；存在材料层面无法解决的悬空引用时
   status=partial 并逐条登记，不得为凑 converged=true 删除引用语句。

## 2. 运行时契约速览

输入 /input/case.json + task.md + 材料；工作 /app/work；交付 /app/output
（result.json 含 case_id + output_contract 全部字段）。预算 64 请求/900 秒。
$S=/skills/weekly-skill/scripts，纯标准库。

## 3. 阶段流程

### Phase 0 — 保底与侦察

```sh
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md \
    --input-dir /input --work /app/work
```

读 inspection.tex_project.bib：backend（bibtex/biber）、bib_files、style；
把 task.md 的引用要求抄成 work/task_items.md（如"样式改 GB/T 7714""合并重复条目"）。

### Phase 1 — 基线：引用链路体检

```sh
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
python3 $S/tex_logscan.py --work /app/work --top 10
python3 $S/cite_audit.py --work /app/work
python3 $S/tex_check.py --work /app/work
```

读 work/cite_report.json：
- C1（error）悬空 \cite 键（file:line）；C2 未被引用条目；C3 疑似重复条目
  （标题相似度≥0.90，给合并建议）；C4 关键字段缺失；C5 样式机制冲突
  （\citep 无 natbib、biblatex 与 \bibliographystyle 并存）；C6 重复 bib key。
- 检查 build_report.passes 是否含 bib 工具轮：没有 bib 轮 = 参考文献表根本不会生成，
  这是"引用全悬空"最常见根因。

### Phase 2 — 链路修复（先通 bib，再修键）

1. bib 链路：backend 与宏包匹配（biblatex+biber、\bibliographystyle+bibtex）；
   .bib 文件缺失按 inspection.missing_refs 处置（材料有则确认路径，无则记
   manual_confirmations）；显式 `--bib bibtex` 或 `--bib biber` 复跑验证。
2. 悬空键（C1）：在 bib 键集合中做近似比对（大小写、年份、作者拼写差异），
   高置信近似才改键名（记 change_log，evidence 写两个键的比对）；无近似键时按
   材料补条目或记 manual_confirmations。
3. 样式冲突（C5）：按 task.md/模板二选一（natbib 或 biblatex），统一 \cite 命令族。

### Phase 3 — 条目治理（去重与补全）

- C3 去重：逐组核对脚本给出的相似对——确认同一文献（标题/作者/年份三者其二一致）
  才合并：保留信息更全的条目，删除另一，正文键名统一为保留键；change_log 记
  `{op:merge_bib, keep, drop, rationale, similarity}`。相似度够但实为不同文献
  （如同名会议不同年份）→ 不合并并在 uncertainty 说明判断。
- C4 补全：缺 author/year/title/journal 的条目，从材料（PDF 参考文献表、任务数据）
  补齐；材料没有 → 留空并记 uncertainty。
- C2 未引用条目：按任务要求处理——保留（加 \nocite{key} 或保持现状）或移除
  （记 change_log）；不得为"干净"默认全删。
- C6 重复 key：合并保留一条，记 change_log。

### Phase 4 — 收敛验证

```sh
python3 $S/cite_audit.py --work /app/work --converge
python3 $S/cite_audit.py --work /app/work
python3 $S/tex_check.py --work /app/work
```

--converge 驱动 tex_build 自动多轮直至无 Rerun 提示（上限 4 轮防死循环）。
验收：build.success=true 且 converged=true（或逐条说明未收敛项）；cite_report 的
error 级（C1/C5/C6）清零；tex_check.undefined_cites=0；参考文献表在 PDF 中实际
生成且条目数与预期一致（目视 preview.pdf 末页）。

### Phase 5 — 交付

写 work/evidence_map.json（每条处置←→finding/材料位置）、change_log.json、
uncertainty.json、manual_confirmations.json、exceptions.json、stats.json：

```sh
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-citation-convergence v1.0.3" --status success   # 或 partial
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

## 4. 异常处置表

| 异常 | 处置 |
|-|-|-|
| bibtex/biber 缺失 | build_report 记录；记 exceptions；bib 问题静态交付 partial |
| .bib 文件缺失 | 材料有则确认路径；无则记 manual_confirmations，正文引用不删 |
| 条目信息材料不全 | 字段留空 + uncertainty；禁止编造 |
| 样式文件 .bst 缺失 | 换可用 .bst（plain→任务指定者不可得时）并记 uncertainty+change_log |
| biber 与 biblatex 版本不匹配 | 日志含 'bcf version' 警告时：改 backend=bibtex 或换 bibtex 兼容方案，记 change_log |
| 合并判据不足 | 不合并，记 uncertainty（宁留重复勿误并） |
| 中文文献著录 | GB/T 7714 需要 gbt7714 宏包/.bst；不可用则记 uncertainty |
| 预算告急（请求>32） | 停止治理，当前状态走 Phase 4/5 交付 partial |

## 5. 预算兜底

Phase 0-1 ≤8 请求；Phase 2-3 每批（一类问题）≤3 请求；Phase 4-5 预留 ≥6。
cite_audit 幂等可复扫，error 数下降为进度信号；两轮无下降即停并登记剩余项。

## 6. work/ 中间文件格式

- change_log.json：`[{"op":"fix_cite_key","file":"intro.tex","line":12,
  "before":"\\cite{knuth84}","after":"\\cite{knuth1984}",
  "reason":"键名笔误；与 bib 键 knuth1984 近似匹配（作者+年份一致）",
  "evidence":"cite_report.json#C1"}]`
- 合并条目：`{"op":"merge_bib","keep":"smith2020j","drop":"smith2020preprint",
  "rationale":"标题相似度0.97、作者一致、保留正式版","evidence":"cite_report.json#C3"}`
- stats.json：`{"cite_marks":N,"bib_entries":M,"errors_initial":X,"errors_final":Y,
  "merged":Z,"converged":true}`

## 7. 参考文件（按需取读）

- references/citation_rules.md — C1-C6 判据、bibtex/biber 链路、合并判据详表
- references/failure_modes.md — 已知失败模式
- examples/minimal_example.md — 合成示例（非正式案例结果）
