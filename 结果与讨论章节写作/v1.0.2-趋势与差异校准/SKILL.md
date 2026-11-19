---
name: results-discussion-trend-calibration
description: 结果与讨论章节写作的"趋势与差异校准"方向技能。当任务要求表述组间差异、剂量/时间趋势和显著性，且需要避免把小波动写成大结论、为"趋势一致但未达显著""仅在高剂量组出现"等边界情形提供规范写法时使用。核心能力：证据强度→措辞强度校准词典、统计支撑邻近性检查脚本（强断言词旁必须有统计量）、有边界的比较句式库。适用于方向、幅度、显著性、组间比较四类表述的校准。
---

# 结果与讨论章节写作：趋势与差异校准方向

## 1. 用途与适用条件

本 Skill 解决科研写作中的**语气强度与证据强度不匹配**：把 p = 0.08 的波动写成"显著提高"；把只在单一条件下出现的现象写成普遍规律；比较只给结论不给基线数值；用"大幅""明显"等无度量形容词替代幅度。基础 Agent 最常见的失分正是这类过度断言。

适用条件：材料含组间比较、梯度或时间序列数据（图/表/统计输出），需撰写结果与讨论章节。

核心原则：

1. **措辞强度 ≤ 证据强度**：每句断言前问"证据支持到哪一级"（显著差异 / 趋势 / 单组现象 / 无差异），从 `reference/calibration_lexicon.md` 选对应级句式。
2. **强断言必带统计锚**："显著""markedly"等词出现的句子必须同句给出统计量（p、CI 或效应量）。
3. **比较必带基线**："A 高于 B"必须给两个数值或明确引用。
4. **边界情形有专用句式**："趋势一致但未达显著""仅在高剂量组出现"不得硬写成确定结论。

## 2. 输入与输出

输入：`/input/case.json`（case_id、output_contract）、`/input/task.md`、`/input/` 科研材料。按扩展名识别文件，不凭标签假设内容。

输出（写入 `/app/output/`）：`result.json`（output_contract 全字段 + case_id + status + sources + uncertainty + change_log）、`results_and_discussion.md`、`calibration_report.json`（校准自检输出）、必要时 docx/PDF 预览。

## 3. 工作流程

### 步骤 1：读契约与材料

同常规流程：读 case.json/task.md，记录 output_contract；用 `reference/tool_recipes.md` 抽取材料。特别要完整抽取**统计检验输出**：每个比较的名称、统计量、自由度、精确 p、效应量、CI、n——它们是本 Skill 的校准基准。

### 步骤 2：为每个比较定级

对材料中的每一对比较/每一条趋势，在 `/app/work/comparisons.md` 中登记一行：

```
C1 对照组 vs 低剂量组: 10.2 ± 1.1 vs 10.9 ± 1.3, p = 0.31 → 级2(无显著差异)
C2 对照组 vs 高剂量组: 10.2 ± 1.1 vs 17.6 ± 1.4, p = 0.002, d = 1.8 → 级1(显著差异,幅度大)
C3 剂量梯度 0/10/20/50 µM: 10.2/10.9/14.8/17.6, 趋势单调 → 级3(趋势,未做趋势检验则标注)
C4 仅 50 µM 组出现细胞形态改变 → 级4(单条件现象)
```

定级规则（与词典联动）：

| 级 | 判据 | 允许措辞 |
|-|-|-|
| 1 显著差异 | p < 0.05（或材料给定的阈值） | "显著升高/降低"（须同句给 p 与效应量） |
| 2 无显著差异 | p ≥ 0.05 | "无显著差异/相当"，禁止"略有升高"暗示趋势 |
| 3 趋势 | p 在 0.05–0.10 或未检验但单调 | "呈上升趋势（未达统计学显著，p = 0.08）" |
| 4 单条件现象 | 仅一个条件出现 | "仅在 50 µM 组观察到……"，禁止推广 |

### 步骤 3：按句式库撰写结果段与讨论段

- 结果段每个比较句从 `templates/comparison_sentence_bank.md` 取对应级句式，填入登记表 C 编号对应的数值与统计量；幅度描述优先给相对量（×1.7、+73%）而非"大幅"。
- 讨论段回顾比较时不得升级措辞：结果段写"呈上升趋势（未达显著）"，讨论段不得写"剂量依赖性提高"——引用必须回指同级措辞。
- 无 p 值的材料：定级最高到级 3（描述性趋势），且句子必须注明"未进行统计学检验"；禁止出现"显著"字样。

### 步骤 4：校准自检

```bash
python3 /skills/weekly-skill/scripts/check_calibration.py \
  --text /app/output/results_and_discussion.md \
  --comparisons /app/work/comparisons.md \
  --out /app/output/calibration_report.json
```

脚本检测（判定细则见 `reference/calibration_rules.md`）：

1. 强断言词（显著、大幅、明显、markedly、significantly、dramatically……）所在句是否含统计锚（p、n=、CI、±、%）；
2. "显著"是否出现在无 p 值的材料语境；
3. 级 2 比较是否被写成方向性结论（检测到"A 高于 B"但登记表 p ≥ 0.05）；
4. 级 4 现象是否被写成普遍规律（句中无"仅/only"限定却引用单条件数据）；
5. 比较句是否缺基线（只有"A 升高"无具体数值或引用）。

未通过项必须修改后重跑至 PASS；确属脚本误报时在 uncertainty 记录。

### 步骤 5：交付

生成 result.json（同 v1 字段规范）、docx/PDF（环境允许时），按 `checklists/final_checklist.md` 自查。

## 4. 异常处理

| 情况 | 处置 |
|-|-|
| 材料只有图无数值与 p 值 | 全部比较定级 3（描述性），句式用"由……升至……"且不出现"显著"；uncertainty 注明"无统计检验输出" |
| 统计输出只给 "p < 0.05" 不给精确值 | 照写 p < 0.05 并注明原文未给精确值 |
| 多重比较未校正 | 在讨论段局限中说明，措辞降半级（"提示而非证实"） |
| 图中无误差棒 | 禁止任何强弱断言，仅做定性描述；uncertainty 注明 |
| 效应量缺失 | 显著句仍须给 p 与 n；效应量在讨论局限中说明缺失 |

## 5. 最小调用示例（示意，非真实案例答案）

输入（示意）：`/input/case.json` 含 `{"case_id":"demo-03","output_contract":["section_md","language"]}`；材料含统计输出：对照组 10.2 ± 1.1 (n=3) vs 低剂量 10.9 ± 1.3 (n=3), p = 0.31；高剂量 17.6 ± 1.4 (n=3), p = 0.002。

调用：抽取统计输出→登记 comparisons.md（C1 级 2、C2 级 1）→按句式库写正文→跑 check_calibration.py 通过→交付。

示意输出（节选）：

```json
{
  "case_id": "demo-03",
  "section_md": "……低剂量组与对照组相当（10.9 ± 1.3 vs 10.2 ± 1.1，p = 0.31，图1B）；高剂量组显著升高至 17.6 ± 1.4（较对照组 +73%，p = 0.002，n = 3，图1C）……",
  "language": "zh",
  "status": "success",
  "sources": {"comparisons": "comparisons.md（工作底稿）", "calibration_report": "calibration_report.json"},
  "uncertainty": [],
  "change_log": ["初稿写'低剂量组略有升高'，按 p=0.31 改为'相当'，避免暗示趋势"]
}
```

## 6. 资源清单

- `scripts/check_calibration.py`：校准自检脚本（stdlib）。
- `reference/calibration_lexicon.md`：证据强度→措辞强度词典（中英）。
- `reference/calibration_rules.md`：自检脚本判定细则。
- `templates/comparison_sentence_bank.md`：分级比较句式库。
- `reference/tool_recipes.md`：材料与统计输出抽取命令。
- `checklists/final_checklist.md`：交付前自查清单。
