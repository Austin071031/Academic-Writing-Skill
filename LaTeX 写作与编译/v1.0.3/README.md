# latex-citation-convergence v1.0.3

LaTeX 引用与参考文献收敛 Skill（玻尔产品周赛·写作13「LaTeX 写作与编译」参赛版，方向：引用与参考文献）。

## 定位

把"键—条目—样式—编译轮次"四环节全部机读化：cite_audit.py 解析全部 \cite 键与
.bib 条目（悬空键 C1、未引用条目 C2、标题相似度去重候选 C3、字段缺失 C4、样式机制
冲突 C5、重复键 C6），并可驱动多轮编译直至交叉引用收敛（--converge）。Agent 只做
需要判断的决策：近似键确认、重复条目合并（判据可解释、留痕）、缺失条目按材料补全。
红线：不臆造文献与字段、合并必须可解释、收敛状态如实报告。

## 组成

SKILL.md＋scripts/（init_result、inspect_case、tex_build、tex_logscan、tex_check、
cite_audit、assemble_result、validate_output，纯标准库）＋references/（citation_rules
判据、failure_modes）＋examples/（合成示例）。

## 快速开始

```sh
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
python3 $S/cite_audit.py --work /app/work
# …链路修复、键修复、条目治理（每批复编）…
python3 $S/cite_audit.py --work /app/work --converge
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-citation-convergence v1.0.3" --status partial
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

## 适用范围与限制

适用：未定义引用修复、bib 整理去重、样式统一、bibtex/biber 链路修复。限制：条目
信息以材料为唯一来源；GB/T 7714 等特定样式依赖相应宏包可用性（不可用则登记）。

仓库：https://github.com/Austin071031/Academic-Writing-Skill （LaTeX 写作与编译/v1.0.3）
