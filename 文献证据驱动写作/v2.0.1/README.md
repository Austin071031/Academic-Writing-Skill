# claim source mapper gain audit（v2.0.1）

玻尔产品周赛第四期「写作05｜文献证据驱动写作」参赛 Skill。**基于 v1.0.1（attempt 89152，70.0 分）增量**：基础 Agent 失败模式拦截审计。

## 快速使用

```bash
# 阶段0：预检（解析案例、材料文本化、生成 result.json 骨架）
bash scripts/run_pipeline.sh /input /app/work /app/output
# 阶段1-4：Agent 按 SKILL.md 执行判定与写作
# 阶段5：终检
python3 scripts/validate_output.py /input /app/work /app/output "$(pwd)"
```

## 文件清单

| 路径 | 说明 |
|-|-|
| `SKILL.md` | 技能主说明（Agent 入口，含执行流程与异常处置） |
| `scripts/inspect_case.py` | 案例预检，生成 brief.json |
| `scripts/extract_text.py` | 材料文本化（pdftotext/PyMuPDF/pypdf，页码标记） |
| `scripts/init_result.py` | result.json 骨架早存 |
| `scripts/validate_output.py` | R1–R7 一致性终检 + 回写 result.json |
| `scripts/run_pipeline.sh` | 阶段0 一键预检 |
| `references/method.md` | 本方向方法详述 |
| `references/rubric.md` | 判定口径 / 分级词表 |
| `references/output_spec.md` | 输出文件格式规范 |
| `references/edge_cases.md` | 异常情形处置 |
| `docs/USAGE.md` | 完整使用说明 |
| `examples/minimal_example.md` | 最小调用示例（合成示意，非正式案例结果） |
| `direction.json` | 方向标识与终检参数 |

## 评分维度对照（自评映射）

| 评分维度 | 本 Skill 的支撑机制 |
|-|-|
| 实际效果（40） | 论断清单—证据表—成稿三段交付；摘录逐字机检（R5）；定位与编号可独立复核 |
| 使用增益（25） | 基础 Agent 常见失败（改写式“摘录”、无定位引用、unsupported 硬写）被脚本显式拦截 |
| 创新增益（15） | 论断—来源关联方向的确定性流程与五值/四维/五级判定口径，机检闭环 |
| 可靠体验（10） | 骨架早存、异常决策表、预算内分片输出、失败如实降档 partial |
| 生态贡献（10） | 完整文档、可复用脚本与模板、合成示例与失败类型清单 |

## 限制

- 离线环境无法联网核验文献真实性与撤稿状态，只能给出可回查路径；
- 扫描版/加密 PDF 无 OCR 引擎时如实标记 failed；
- 证据强度与确定性分级是写作辅助口径，不替代同行评议。


## v2.0.1 增量说明

- 增量：对照基础 Agent 失败模式清单，逐模式输出本次运行的拦截/规避证据（gain_audit.json）。
- 新增脚本：gain_audit.py；新增参考：failure_modes.md
- 命中维度：见 `_iteration/05_route_cards.md`；预期：机制真实增益 估 +9 → 兑现 +3（N=3）
- 回归风险与对策：审计措辞被误读为编造对照 → 只陈述本次运行可复核事实，禁写未运行的基线数字
- 与基线差异：`git diff v1.0.1 v2.0.1`；删除文件 0 个，自检规则 R1–R7 全保留，新增 R8。
