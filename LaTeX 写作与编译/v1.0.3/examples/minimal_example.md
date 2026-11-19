# 最小调用示例（合成示例，非正式案例结果）

> 以下为说明接口与流程的合成示例，不代表平台正式案例结果。

## 示例输入（合成，含 4 个植入缺陷）

main.tex 节选：
```tex
\documentclass{article}
\begin{document}
文献 \cite{knuth84} 与 \cite{lamport1994,ghost2025} 已有论述。
\bibliographystyle{plain}
\bibliography{refs}
\end{document}
```
refs.bib：
```bibtex
@article{knuth1984, author={Knuth, Donald E.}, title={Literate Programming},
  journal={The Computer Journal}, year={1984}}
@book{lamport1994, author={Lamport, Leslie}, title={LaTeX: A Document Preparation System},
  year={1994}, publisher={Addison-Wesley}}
@misc{lamport94, author={Lamport, Leslie}, title={LaTeX: A Document Preparation System},
  year={1994}, note={Addison-Wesley}}
```

缺陷：`knuth84` 键名笔误（实为 knuth1984，C1）；`ghost2025` 无条目（C1）；
lamport1994 与 lamport94 疑似重复（C3，标题相似度 1.0）；lamport94 未被引用（C2）。

## 调用

```sh
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
python3 $S/cite_audit.py --work /app/work
python3 $S/cite_audit.py --work /app/work --converge
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-citation-convergence v1.0.3" --status partial
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

## 示意输出（合成）

```
[cite_audit] 引用点=3 唯一键=3 bib条目=3 findings=4
  [C1/error] main.tex:3 \cite{knuth84}（近似键 knuth1984）
  [C1/error] main.tex:3 \cite{ghost2025}（无近似键）
  [C3/warn] lamport1994 ≈ lamport94（相似度 1.00）→ 建议保留 lamport1994
  [C2/info] lamport94 未被引用
```

处置：knuth84→knuth1984（作者+年份一致，change_log 记比对依据）；合并 lamport94 入
lamport1994（keep/drop/rationale 留痕）；ghost2025 材料无条目信息 →
manual_confirmations 登记，引用保留。因 ghost2025 无法在材料内解决，
status=partial、converged=false 如实报告，uncertainty 逐条说明。
