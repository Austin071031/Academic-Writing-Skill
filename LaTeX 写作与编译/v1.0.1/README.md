# latex-math-consistency v1.0.1

LaTeX 数学公式一致性与排版合规审查修复 Skill（玻尔产品周赛·写作13「LaTeX 写作与编译」参赛版，方向：改得对·公式）。

## 定位

基础 Agent 改公式靠肉眼逐段读，漏检率高且无留痕。本 Skill 用 math_audit.py 对全部
公式环境做机读普查（M1 显示数学写法、M2 eqnarray、M3 编号/引用一致性、M4 文字下标
正体、M5 单位 siunitx、M6 裸算子、M7 \left/\right 配对），产出带 file:line 与改法
建议的 findings；Agent 只做语义判断与精确编辑，全部修改留痕可复核，最终以
"编译收敛 + 静态复扫 findings 清零"双通道验收。

## 组成

SKILL.md（流程）＋ scripts/（init_result、inspect_case、tex_build、tex_logscan、
tex_check、math_audit、assemble_result、validate_output，纯标准库）＋
references/（math_rules 判据、failure_modes）＋ examples/（合成示例）。

## 快速开始

```sh
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
python3 $S/math_audit.py --work /app/work
# …按 findings 分批修复并复编…
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag final --until-converge
python3 $S/math_audit.py --work /app/work
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-math-consistency v1.0.1" --status partial
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

## 适用范围与限制

适用：公式改写/校对、编号与引用整理、单位与符号规范、定理环境整理、数学模式编译错误。
限制：不改公式数学含义（无任务/材料依据时）；PDF 转写时看不清的符号只登记不猜测。

仓库：https://github.com/Austin071031/Academic-Writing-Skill （LaTeX 写作与编译/v1.0.1）
