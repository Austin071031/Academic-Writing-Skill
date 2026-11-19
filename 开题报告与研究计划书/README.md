# 开题报告与研究计划书（写作15）— 五方向参赛 Skill 集

围绕赛题“开题报告与研究计划书：学术写作：完成产物，也保留来源”的 5 个截然不同方向的 Skill 版本。五个版本共享同一套运行契约与交付管线，但各自的主工件、核心方法与校验侧重不同，可独立提交、独立评测。

| 版本 | 方向 | 主工件 | 解决的核心失分点 |
|---|---|---|---|
| v1.0.0-研究缺口与证据提炼 | 研究背景与缺口提炼 | 证据清单 + 已知—未知—待验证矩阵 | 背景写成领域综述、缺口无证据支撑 |
| v1.0.1-问题定义与目标对齐 | 问题定义与目标设定 | 假设—检验矩阵 + 对齐追踪矩阵 | 目标/路线/成果各写各的、指标阈值无依据 |
| v1.0.2-技术路线与阶段规划 | 技术路线与阶段计划 | 步骤依赖图 + 资源核算表 + 甘特图 | 计划排不进周期、经费超支、里程碑无验收标准 |
| v1.0.3-风险识别与备选方案 | 风险与备选方案 | 风险登记册（触发信号/备选/决策时点） | 风险章节空泛、风险与计划两张皮 |
| v1.0.4-引用溯源与可编辑交付 | 引用证据与可编辑交付 | 论断—来源映射表 + md/docx/pdf/png 管线 | 引用无法回溯、交付不可编辑、预览伪造 |

## 共同的运行契约（评测环境）

- 输入：`/input/case.json` + `/input/task.md`，为唯一事实来源，不补造材料外事实。
- 工作目录 `/app/work`；最终产物 `/app/output`，必须含 `result.json`（`output_contract` 全字段 + `case_id` + `status` + `artifacts` + `sources` + `uncertainty` + `change_log`）。
- 交付可编辑 `proposal.md`/`proposal.docx` 与真实渲染的 PDF/PNG 预览；渲染失败降级 `partial` 并记录，不伪造。
- 质量自检：`scripts/validate_proposal.py --profile <方向>`；交付构建：`scripts/build_output.py`。

## 目录结构（每个版本相同）

```
vX.x.x-<方向>/
├── SKILL.md            # Skill 本体（YAML frontmatter + 完整流程）
├── README.md / 使用说明
├── GITHUB_URL.txt      # 本平台提交用 GitHub 链接
├── templates/          # 方向模板 + 七要素稿件模板
├── checklists/         # 质量检查表（按评分四问分组）
└── scripts/            # validate_proposal.py / build_output.py
```

## 依赖

Python 3.8+（标准库）；可选渲染工具：pandoc、libreoffice（soffice）、pdftoppm、matplotlib（甘特图）。全部缺失时仍产出 md 与 result.json，status=partial。

## 维护

- 版本迭代：在同目录新建 `v1.1.0-<方向>` 文件夹，保留旧版本。
- 新题目：在仓库根新建题目文件夹，沿用“题目/版本-方向”结构。
