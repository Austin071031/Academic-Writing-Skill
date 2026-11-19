# 最小调用示例（合成示例，非正式案例结果）

> 以下为说明接口与流程的合成示例；输入为人工构造的破损工程，输出为示意，
> 不代表平台正式案例的结果。

## 示例输入（合成）

/input/case.json：
```json
{"case_id": "demo-broken-001",
 "output_contract": {"deliverables": "可编辑tex工程", "verification": "编译验证记录",
                     "changes": "修改记录", "uncertainties": "不确定性说明"}}
```

/input/task.md：「修复该工程使其编译通过、交叉引用收敛；保持正文内容不变。」

/input/main.tex（节选，含 3 个植入缺陷）：
```tex
\documentclass{article}
\usepackage{amsmath}
\begin{document}
见式 \eqref{eq:e} 与表 \ref{tab:x}\cite{missing2024}。
\begin{equation}e^{i\pi}+1=0\label{eq:e}\end{equation}
\begin{table}[h]\caption{示例}\label{tab:x}
\begin{tabular}{lc}\toprule 项目 & 值 \\\midrule 甲 & 1 \\\bottomrule\end{tabular}
\end{table}
\end{document}
```
缺陷：未加载 booktabs（\toprule 未定义，级联）；\cite 键在 bib 中不存在；缺 .bib 文件。

## 调用

```sh
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
python3 $S/tex_logscan.py --work /app/work --top 10
python3 $S/tex_check.py --work /app/work
python3 $S/safe_fix.py --work /app/work
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag final --until-converge
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-compile-rescue v1.0.0" --status partial
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

## 示意输出（合成，节选）

logscan 分诊：
```
[tex_logscan] 错误=3 警告=1 分类={'undefined_control_sequence': 3}
[tex_logscan] 根因假设: 首个未定义命令疑似缺宏包 booktabs，其后同类错误多为级联
```
safe_fix：`修复 1 处: add_package（\usepackage{booktabs}）`，自动写 fix_log.json。
tex_check：`悬空 cite=1（missing2024）` → 记入 manual_confirmations（材料无该条目信息）。
最终：final 编译 success=true；因 citation 缺失材料不可补，status=partial，
uncertainty 注明「\cite{missing2024} 无来源条目，保留待人工处理」。

## 示意 result.json 骨架（合成）

```json
{"case_id": "demo-broken-001", "status": "partial",
 "skill": "latex-compile-rescue v1.0.0",
 "build": {"engine": "pdflatex", "success": true, "converged": false, "passes": 4},
 "change_log": [{"op": "add_package", "file": "main.tex", "line": 3,
                 "after": "\\usepackage{booktabs}",
                 "reason": "\\toprule 未定义；白名单命令→宏包映射",
                 "evidence": "build_baseline.log"}],
 "manual_confirmations": [{"item": "\\cite{missing2024} 无 bib 条目", "blocking": false}],
 "uncertainty": [{"item": "参考文献条目缺失", "reason": "材料未提供条目信息"}]}
```
