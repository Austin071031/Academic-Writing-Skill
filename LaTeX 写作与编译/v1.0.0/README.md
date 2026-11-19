# latex-compile-rescue v1.0.0

LaTeX 编译错误诊断与迭代修复闭环 Skill（玻尔产品周赛·写作13「LaTeX 写作与编译」参赛版，方向：编译得通）。

## 它解决什么问题

Agent 面对一个编译失败的 LaTeX 工程时，常见失败是：被第一条错误之后的几十条级联
错误淹没、逐条硬修、预算耗尽且无产出、为凑编译删内容、或声称修好却无法复核。
本 Skill 把流程工程化：**基线编译 → 日志分诊（根因 vs 级联）→ 白名单机械修复 →
语义修复（逐条留痕）→ 收敛验证 → 结构化交付**，每步都有脚本产出可复核的 JSON 证据。

## 组成

| 文件 | 作用 |
|-|-|
| SKILL.md | Agent 流程说明（阶段、红线、异常表、预算兜底） |
| scripts/init_result.py | 开跑即落盘 result.json 骨架，防超时空手 |
| scripts/inspect_case.py | 侦察 case.json/task.md/材料，识别主文件、引擎、缺失引用，暂存工程 |
| scripts/tex_build.py | 多轮编译封装：引擎探测、bib 链路、收敛判断、超时保护、报告落盘 |
| scripts/tex_logscan.py | 日志解析：错误分类、file:line 定位、级联根因归并 |
| scripts/tex_check.py | 源码静态审查：交叉引用/bib 键/环境配平/占位符/元数据 |
| scripts/safe_fix.py | 白名单机械修复（补宏包、引擎魔法注释、缺失 input 占位），自动留痕 |
| scripts/assemble_result.py | 汇总交付：可编辑工程 + PDF 预览 + 报告 + 契约化 result.json |
| scripts/validate_output.py | 交付闸门：契约字段、case_id、可编辑产物核查 |
| references/ | 错误分类体系、修复剧本、失败模式 |
| examples/ | 合成案例调用示例（非正式案例结果） |

全部脚本仅依赖 Python3 标准库；TeX 引擎缺失时如实降级，不伪造编译结论。

## 快速开始（Agent 用法）

```sh
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
python3 $S/tex_logscan.py --work /app/work --top 15
python3 $S/safe_fix.py --work /app/work
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag final --until-converge
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-compile-rescue v1.0.0" --status partial
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

详见 docs/USAGE.md 与 SKILL.md。

## 适用范围与限制

- 适用：含 .tex 源码的工程修复、编译排错、投稿前编译合规整理、按任务要求做有限改写。
- 限制：不做全文润色；不重建缺失图片内容；bib 条目信息以材料为唯一来源；
  模板类文件缺失时以通用类兜底并声明版式不保真。

## 维护

- 版本：v1.0.0（2026-11）。改动记录见 CHANGELOG.md。
- 仓库：https://github.com/Austin071031/Academic-Writing-Skill （LaTeX 写作与编译/v1.0.0）
