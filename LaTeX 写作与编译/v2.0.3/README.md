# latex-template-reproducible-build v2.0.3（基于 v1.0.4 增量）

LaTeX 模板适配与可重复构建 Skill（玻尔产品周赛·写作13「LaTeX 写作与编译」参赛版，方向：模板适配 + 复现得了）。

## 与基线 v1.0.4 的差异（唯一改动）

新增 `scripts/template_fix.py` + `direction.json`：把 template_audit 的 P1/P3/P4 发现
转为受限机械修复——必填元数据 TODO 骨架插入（内容交 Agent 从材料回填，登记
manual_confirmations）、hyperref 加载顺序机械调整、过时宏包白名单替换，全部留痕。
基线是"只审不修"，本版补成"审修闭环"中安全机械的那一环；语义迁移仍由 Agent 执行。
基线其余资产原样保留。

## 定位

template_audit.py 按文档类识别必填元数据（IEEEtran/elsarticle/acmart/ctexart 等内置表）、
审计导言区（五组宏包冲突对、hyperref/cleveref 加载顺序、过时宏包与命令）、与模板
示例做差异比对（缺载宏包、规定 .bst）；build_manifest.py 生成 BUILD_MANIFEST——
引擎/工具/宏包版本（只来自真实 --version 与编译日志）、源码 sha256、精确命令序列与
轮次，使他人按记录复现同一 PDF。Agent 做迁移决策与内容回填（内容只来自材料）。

## 组成

SKILL.md＋scripts/（init_result、inspect_case、tex_build、tex_logscan、tex_check、
template_audit、build_manifest、assemble_result、validate_output，纯标准库）＋
references/（template_rules、failure_modes）＋examples/（合成示例）。

## 快速开始

```sh
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/template_audit.py --work /app/work --template /app/work/project   # 或模板目录
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag baseline --until-converge
# …按 P1-P5 逐项迁移适配（每批复编）…
python3 $S/tex_build.py --project /app/work/project --work /app/work --tag final --until-converge
python3 $S/build_manifest.py --work /app/work
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
    --skill "latex-template-reproducible-build v2.0.3" --status partial
python3 $S/validate_output.py --out /app/output --case /input/case.json
```

## 适用范围与限制

适用：模板迁移、模板合规审计、导言区整理、构建工程化与复现清单。限制：模板类文件
缺失时以可用类兜底并声明版式不保真；版本信息取不到时如实写 unknown。

仓库：https://github.com/Austin071031/Academic-Writing-Skill （LaTeX 写作与编译/v2.0.3）
