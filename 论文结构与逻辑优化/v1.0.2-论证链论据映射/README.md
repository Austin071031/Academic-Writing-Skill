# argument-chain-audit（论证链与论据对应）v1.0.2

论文结构与逻辑优化 Skill：**主攻论证链与论据对应**，六维普查兜底覆盖。

## 它解决什么问题

基础 Agent 审稿件时给出的大多是"论据要充分"这类通用写作原则。本技能把"论断—论据"对应关系做成**可机检的映射**：

- 论断抽取：逐句命中论断提示词并分类（比较论断/因果论断/概括论断/绝对论断）；
- 论据锚点：每句/每段检测引用 [n]/作者年、图表/公式/章节交叉引用、带单位数字；
- 论断—论据映射表：每条论断三档裁决——strong（同句或同段有锚点）/ weak（相邻段有锚点）/ none（窗口内无锚点即断裂）；
- 深度检查：跨段逻辑跳跃（新术语突现且无论据）、疑似循环论证（3-gram 相似+双无锚点）、论据强度不足（因果/绝对论断只有相关性或单点数据）、比较论断无对象。

每条问题定位到 **章节 › 段落 › 句子** 并附原文锚点与 9 类编辑动作之一（move/merge/split/narrow/qualify/add/add_transition/add_limitation/reorder），输出**编辑计划而非改写稿**。

## 快速开始

```bash
# 平台环境（/input 有 case.json/task.md/稿件）
python3 scripts/init_result.py
python3 scripts/inspect_case.py --work /app/work
python3 scripts/parse_manuscript.py --work /app/work
python3 scripts/six_scan.py --work /app/work
python3 scripts/chain_audit.py --work /app/work
python3 scripts/report_builder.py --work /app/work --out /app/output \
  --focus argument_chain --skill "argument-chain-audit v1.0.2"
# → 人工/Agent 复核 diagnosis_report.md（删误报/补漏报/定优先级）
python3 scripts/assemble_result.py --work /app/work --out /app/output \
  --skill "argument-chain-audit v1.0.2" --status success
python3 scripts/validate_output.py --out /app/output --work /app/work
```

完整说明见 [docs/USAGE.md](docs/USAGE.md)；最小调用示例见 [examples/minimal_example.md](examples/minimal_example.md)。

## 目录

- `SKILL.md` — 技能本体（Agent 工作流）
- `scripts/` — 纯标准库 Python3 管线（零依赖；PDF 抽取可选依赖 pdftotext）
- `references/` — 判据、分类、标注示例、误报模式
- `docs/USAGE.md` — 使用与方法说明、失败处理、自查
- `evaluation/` — 评分自查表、合成测试文本
- `examples/` — 最小调用示例（示意输出已标注）

## 兼容与限制

Python ≥ 3.8，无第三方依赖；稿件格式 md/txt/tex/docx/pdf。阈值集中于 `scripts/scanutil.py:THRESH` 与 `scripts/chain_audit.py:TH`，可复核可调。循环论证为近似判定、词面锚点漏检导致的假断裂需人工复核（见 references/failure_modes.md）。
