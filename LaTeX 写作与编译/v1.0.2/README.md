# latex-table-governance v1.0.2

LaTeX 表格与浮动体治理 Skill（玻尔产品周赛·写作13「LaTeX 写作与编译」参赛版，方向：改得对·表格）。

## 定位

table_audit.py 对工程内全部 tabular/table 逐表体检：列数一致性（含 \multicolumn 展开）、
caption/label 有无与位置、\hline vs booktabs、\resizebox 缩放包裹（题面明确反对的
掩盖手段）、浮动位置 [h]/[H]、超宽与跨页启发式嫌疑；支持两个受限机械修复
（简单 \hline → booktabs 三线表、浮动位置放宽 [htbp]），自动留痕。语义问题（数据、
结构、跨页方案）交 Agent 按判据处理，最终"编译收敛 + 复扫清零 + PDF 目视"三重验收。

## 组成

SKILL.md＋scripts/（init_result、inspect_case、tex_build、tex_logscan、tex_check、
table_audit、assemble_result、validate_output，纯标准库）＋references/（table_rules
判据与改造范式、failure_modes）＋examples/（合成示例）。

## 快速开始

```sh
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
python3 $S/table_audit.py --work /app/work
python3 $S/table_audit.py --work /app/work --apply-booktabs --apply-float-htbp
# …语义修复（每表改完复编）…
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag final --until-converge
python3 $S/table_audit.py --work /app/work
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-table-governance v1.0.2" --status partial
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

## 适用范围与限制

适用：表格修复/三线表改造/宽表跨页/浮动整理/题注规范。限制：表内数据以材料为唯一
来源；超宽表分流方案按模板约束选择；启发式超宽报警需 PDF 目视确认。

仓库：https://github.com/Austin071031/Academic-Writing-Skill （LaTeX 写作与编译/v1.0.2）
