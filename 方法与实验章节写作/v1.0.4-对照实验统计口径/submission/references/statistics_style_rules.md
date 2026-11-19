# 实验矩阵、可比性与统计口径规则（v1.0.4）

## 1. 实验矩阵字段（work/experiment_matrix.json）

| 字段 | 必填 | 说明 |
|-|-|-|
| rid | ✓ | R1…Rk，正文引用编号 |
| variant | ✓ | 变体/模型/基线名称 |
| is_baseline | ✓ | 基线行 true |
| dataset / split / metric | ✓ | 一行只填一对 metric×split |
| budget | ✓ | 训练预算（epoch 数/FLOPs/时长）；同预算是对比前提 |
| seed / repeats | ✓ | 重复次数与种子 |
| value | ✓ | 材料中的结果值；没有填"未在材料中给出"并进 gaps |
| mean / std / ci / sem | repeats>1 必填其一离散度 | 无则闸门记 missing_stats |
| single_run_note | repeats=1 必填 | 如"单次运行结果，未做显著性检验" |
| source_eid | 有值必填 | 结果值的证据锚点 |
| *_waiver | 不一致时必填 | 豁免理由 |

## 2. 可比性判定

- 可比：dataset、split、metric、budget 全部一致，或差异有 waiver 说明且正文交代。
- 不可比：上述任一不一致且无 waiver——正文不得写"优于"，改写"在各自预算下，
  R1 取得 X；与 R2 的直接比较受预算差异影响"。

## 3. 统计口径句式

- 多次重复："3 个种子下 Accuracy 为 91.3±0.4（均值±标准差）〔E#〕"。
- 单次运行："单次运行（seed=42）Accuracy 为 91.3%〔E#〕，未做显著性检验"。
- 读图估计："论文图 3 显示基线约为 89%（读图估计，材料未给出精确值）"。
- 禁止：编造 p 值、置信区间、"显著优于"（无检验支撑时）。

## 4. 结论措辞三档

- **表明**：多种子均值有离散度支撑且差距大于离散度；或材料直接给出检验结论。
- **初步表明**：单次运行或离散度与差距同量级。
- **有望**：消融趋势一致但未在测试集验证。
正文比较句的动词必须与该档一致，引擎人审对照 statistics_style_rules 抽查。
