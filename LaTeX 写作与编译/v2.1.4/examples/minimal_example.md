# 最小调用示例（合成示例，非正式案例结果）

> 以下为说明接口与流程的合成示例，不代表平台正式案例结果。

## 示例输入（合成）

任务：把 article 稿件迁入材料自带的 IEEE 风格模板（template/ieee_sample.tex 规定
\bibliographystyle{IEEEtran} 与 IEEEkeywords 结构）。

main.tex 节选（含 4 个植入缺陷）：
```tex
\documentclass{article}
\usepackage{natbib}
\usepackage{biblatex}
\usepackage{hyperref}
\usepackage{amsmath}
\title{实验研究}
\author{作者甲}
\begin{document}
\maketitle
正文……\bibliographystyle{plain}\bibliography{refs}
\end{document}
```
缺陷：缺 abstract/keywords（P1，按目标类要求）；natbib×biblatex 冲突（P2）；
hyperref 后仍加载 amsmath（P3）；样式与模板规定不符（P5b：应为 IEEEtran）。

## 调用

```sh
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/template_audit.py --work /app/work --template /app/work/project/template
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
# …迁移适配…
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag final --until-converge
python3 $S/build_manifest.py --work /app/work
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-template-reproducible-build v2.1.4" --status success
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

## 示意输出（合成）

```
[template_audit] 类=article 宏包=4 findings=4
  [P1/error] abstract: 目标类要求 abstract 环境，源码未检出
  [P2/error] natbib×biblatex: 两种参考文献机制互斥
  [P3/warn] hyperref: hyperref 之后仍加载: amsmath
  [P5b/warn] bibliographystyle: 模板规定 IEEEtran
[manifest] 引擎=pdflatex 工具版本=4 宏包版本=9 源文件=3 命令=4
```

处置：按模板换类与元数据结构、摘要从原文回填、保留 biblatex 去 natbib（模板说明
依据记入 change_log）、hyperref 移至宏包区末尾、\bibliographystyle{IEEEtran}；
build_manifest 生成含真实版本与 4 轮命令序列的 BUILD_MANIFEST.md。
