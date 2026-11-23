# 完整走查示例（合成文本，仅演示流程，非任何正式案例结果）

## 输入片段（合成）

> 我们提出了一种新的算法，可以比传统方法更快。实验结果显示，准确率达到92.4%。结果证明，该方法适用于大规模场景。

## 术语表（terminology.py build 抽取后 Agent 确认）

| preferred_form | abbreviation | 处置 |
|-|-|-|
| 均方根误差 / root mean square error | RMSE | 首现补全称（Agent 引入的写法已登记 variant） |

## 逐句决策（chunk 行节选）

```jsonl
{"id":"demo-B1-P1-S1","original":"我们提出了一种新的算法，可以比传统方法更快。","polished":"本文提出一种新算法，其速度优于传统方法。","decision":"modify","types":["register","clarity"],"reason":"去人称主语；“更快”改“速度优于”表达更明确"}
{"id":"demo-B1-P1-S2","original":"实验结果显示，准确率达到92.4%。","polished":"实验结果显示，准确率达到92.4%。","decision":"keep","types":[],"reason":"无语病；数值必须原样保留"}
{"id":"demo-B1-P1-S3","original":"结果证明，该方法适用于大规模场景。","polished":"结果表明，该方法可能适用于大规模场景。","decision":"modify","types":["hedging"],"reason":"单数据集结果不足以支撑“证明”；降级至同证据强度档需作者确认"}
```

## 审校通道的拦截

guard_check 会对 S3 报 **critical/hedging（0→2 实为跨档）**：原文"证明"是档位 0，
改文"表明…可能"是档位 1+2，强度被削弱。正确处置二选一：
1. 改回"结果证明"（最小编辑，推荐——润色无权替作者降级主张）；或
2. 确需降级时，在 resolutions.jsonl 记录 `{"flag_id":"demo-B1-P1-S3","kind":"hedging","action":"justified","note":"单数据集证据不足以支撑'证明'，已与作者主张核对"}`，
   并写入 manual_review_required 提示作者确认。

**要点**：守恒检查宁可误报、不可漏报；每条 critical 都有去向（改正或记录在案）。

## 产物片段（change_log.md 节选）

| ID | 原文 | 改文 | 类型 | 理由 |
|-|-|-|-|-|
| demo-B1-P1-S1 | 我们提出了一种新的算法，可以比传统方法更快。 | 本文提出一种新算法，其速度优于传统方法。 | register, clarity | 去人称主语；比较表达明确化 |
| demo-B1-P1-S2 | 实验结果显示，准确率达到92.4%。 | （保留） | — | 无语病，数值守恒 |
| demo-B1-P1-S3 | 结果证明，该方法适用于大规模场景。 | （保留/降级，见审校报告处置记录） | hedging | 见 resolutions |
