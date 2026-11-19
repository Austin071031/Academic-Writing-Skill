# contribution-evidence-alignment v1.0.3｜贡献对得上

参赛 Skill 版本之四，主攻**贡献表述**方向：贡献卡片化（contributions.json），
引擎逐条核验证据位置可解析、数字可回溯、范围词有比较性数据支撑（否则转人工确认），
渲染 contributions_check.md 对照表，保证每条贡献与本文方法、图表、实验结果一一对应。

## 适用场景

- 起草/修改引言贡献段；
- 核对贡献表述与实际方法、图表、结果的一致性；抑制夸大。

## 快速开始

共享管线 + Phase 3 登记 contributions.json → Phase 4 `contribution_align.py` + `build_deliverables.py` →
assemble/validate/render。详见 [docs/USAGE.md](docs/USAGE.md)。

## 依赖与边界

- Python 3.8+ 纯标准库。
- 贡献核验依赖稿件质量；稿件缺失时按 SKILL.md 降级路径执行。

## 仓库

https://github.com/Austin071031/Academic-Writing-Skill （目录：引言与相关工作写作/v1.0.3-贡献证据对齐）
