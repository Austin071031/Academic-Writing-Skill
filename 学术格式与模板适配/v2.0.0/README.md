# 学术格式与模板适配 · v2.0.0

基于 **v1.0.1**（attempt 89028）的契约层加固版。方向不变（模板适配全流水线），
本版唯一改的事：**保证无论流水线在何处失败，/app/output/result.json 必然合法存在**，
并补全材料兜底扫描与 900s 预算守卫。输出契约键名/结构零改动。

## 与基线差异（评分对照）

| 修复项 | 弃权型缺口 | 归属评分维度 | 证据 |
|-|-|-|-|
| 顶层崩栈 guard + 应急 result.json | C1/C2 中断无合法产物 | 可靠体验(10)/结果完整性(5) | p4 模拟：基线零产物 → v2.0.0 合法 result.json |
| 材料/模板兜底扫描含 case.json 目录 | C3 非标准挂载找不到材料 | 任务完成度(15)/异常处理(3) | p2 实测：基线 failed → v2.0.0 success |
| pdftotext 单次调用 form-feed 分页 | C4 长文档压 900s 预算 | 运行稳定性(4) | 代码路径审查 |
| soffice 独立 UserInstallation | C5 HOME 只读/并发风险 | 运行稳定性(4) | 代码路径审查 |
| direction.json 读取并记录 | C6 跨题资产未迁移 | 生态贡献(10) | uncertainty.notes 实测出现 |

回归：`regression_report.json` verdict=pass——资产白名单 0 缺失、R1–R10 守恒规则零删除、
契约键逐一同、行为 parity（9 阶段 / compliance 21 PASS / fidelity PASS）全同、
删除文件 = 0、新增文件 = direction.json + 本目录文档。

## 文件

同 v1.0.1，新增 `direction.json`、`SUBMISSION.md`、`README.md`、`CHANGELOG.md`；
`_iteration/` 为本次迭代的台账/契约/裁决/路线卡/回归/代理评测记录。

## 调用（与基线一致）

```bash
python3 /skills/weekly-skill/scripts/run_pipeline.py \
    --case /input/case.json --task /input/task.md \
    --work /app/work --outdir /app/output
```
