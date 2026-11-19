# 数值台账（evidence ledger）字段规范

台账是正文数值的唯一事实来源。写正文前先建台账；正文数值核验（verify_numbers.py）以台账为基准。

## 条目结构

```json
{
  "id": "唯一标识，建议 {来源}-{面板}-{物理量缩写}",
  "source": "图2B | 表3 | 补充图S1A | stats_output.txt 第14行",
  "panel": "2B",
  "quantity": "细胞存活率 / cell viability",
  "value": 87.3,
  "unit": "%",
  "error": {"type": "SD", "value": 4.1},
  "n": 3,
  "stat": {"test": "one-way ANOVA + Tukey", "p": 0.002, "vs": "对照组", "df": "2,12"},
  "quote": "图注原文: Data are mean ± SD (n = 3)",
  "confidence": "high"
}
```

## 字段填写规则

| 字段 | 规则 |
|-|-|
| id | 全局唯一；派生量（如 fold change）须新登记一条并注明 `derived_from` |
| source | 写到可定位的最小单元：子面板（图2B）优于整图（图2）；统计输出写到行号 |
| value | 纯数值，不带单位、不带逗号（写 12345.6 而非 12,345.6） |
| unit | 国际单位或图中单位，全篇统一换算规则见 reference/units_and_errors.md |
| error.type | SD / SEM / CI95 / IQR / range / unknown；判据见 units_and_errors.md，判不出用 unknown 并配合 confidence=medium |
| n | 生物学重复数；图中无 n 时查方法部分；仍无则省略并写 uncertainty |
| stat | 检验名、精确 p（写 0.002 而非 <0.05，若原文只给 <0.05 则照抄并注明）、对比基准、自由度、效应量与 CI |
| quote | 一句话说明该数值从何处、如何读出（图注原文 / 表中第几行第几列 / 位图读数） |
| confidence | high=表或统计输出直接读出；medium=位图读数；low=勉强可读，正文须加 [待核实] |

## 覆盖要求

- 正文（结果段+讨论段）中每一个阿拉伯数字都必须能在台账中找到。
- 算术汇总值（百分比变化、倍数）允许存在，但必须单独登记并在 quote 中写明计算式，如 `"quote": "计算: (87.3-61.4)/87.3 = 29.7% decline"`。
- 台账条目数与正文数值数大致相当；核验报告出现 unmatched 即说明台账漏登或正文写错。
