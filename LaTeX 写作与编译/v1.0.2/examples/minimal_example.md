# 最小调用示例（合成示例，非正式案例结果）

> 以下为说明接口与流程的合成示例，不代表平台正式案例结果。

## 示例输入（合成 main.tex 节选，含 4 个植入缺陷）

```tex
\documentclass{article}
\usepackage{booktabs}
\begin{document}
结果见表 \ref{tab:r}。
\begin{table}[h]
\begin{tabular}{lcc}
\hline
方法 & 精度 & 召回 \\
\hline
甲 & 0.91 & 0.88 \\
乙 & 0.93 \\
\hline
\end{tabular}
\caption{实验结果}\label{tab:r}
\end{table}
\end{document}
```

缺陷：行 2 只有 2 列（列声明 3 列，T3 error）；仅 \hline（T4）；浮动位置 [h]（T6）；
caption 在 tabular 之后（T2，按"表题在上"惯例）。

## 调用

```sh
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
python3 $S/table_audit.py --work /app/work
python3 $S/table_audit.py --work /app/work --apply-booktabs --apply-float-htbp
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag final --until-converge
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-table-governance v1.0.2" --status success
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

## 示意输出（合成）

```
[table_audit] 表格=1 findings=4
  [T3/error] main.tex:10 该行解析出 2 列，与列声明 3 列不一致
  [T2/info] caption 位于 tabular 之后
  [T4/warn] 仅 \hline → booktabs 三线表
  [T6/warn] 浮动位置 [h] → [htbp]
[table_audit] 机械修复=4（hline→booktabs ×3、float [htbp] ×1）
```

Agent 手工修 T3（补缺失单元格，数据依材料）并上移 caption，记 change_log 2 条；
final 编译 success=true、复扫 findings=0，status=success。
