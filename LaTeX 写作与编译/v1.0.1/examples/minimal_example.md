# 最小调用示例（合成示例，非正式案例结果）

> 以下为说明接口与流程的合成示例，不代表平台正式案例结果。

## 示例输入（合成 main.tex 节选，含 5 个植入缺陷）

```tex
\documentclass{article}
\usepackage{amsmath}
\begin{document}
由式 \eqref{eq:main}，取最大值 $x_{max}$，损耗 $P = 10 W$。
$$
E = m c^2 \label{eq:main}
$$
\begin{eqnarray}
y &=& sin(x) + 1
\end{eqnarray}
\end{document}
```

缺陷：`$$` 显示数学；eqnarray；`x_{max}` 斜体文字下标；`10 W` 数学模式斜体单位；
`sin` 裸算子；另有 \eqref 与 eqnarray 行编号策略待任务确认。

## 调用

```sh
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
python3 $S/math_audit.py --work /app/work
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag final --until-converge
python3 $S/math_audit.py --work /app/work
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-math-consistency v1.0.1" --status success
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

## 示意输出（合成）

```
[math_audit] 公式环境={'eqnarray': 1} findings=5
  [M1/warn] main.tex:5 $$...$$ 改用 \[...\]
  [M2/warn] main.tex:8 eqnarray → align（&=& → &=）
  [M4/info] main.tex:3 _{max} → _{\mathrm{max}}
  [M5/info] main.tex:3 $10 W$ → \qty{10}{\W}（siunitx）
  [M6/warn] main.tex:9 sin → \sin
```

修复后 change_log 5 条（每条 evidence 指向 math_report finding），
final 编译 success=true、math_report findings=0，status=success。
