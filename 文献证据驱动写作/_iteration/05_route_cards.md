# 阶段 5 路线卡（route cards）

基线 v1.0.1 / attempt 89152 / 70.0 分；N=3（预期均已折算）；§0-5 = 4 版 → 从末位截去组合版，保留共性短板位次 1–2 + 单点 2 张。每版 = 基线超集 + 唯一一件增量。

```
R1 → v2.0.0（基线 v1.0.1 / 89152 / 70.0 分）
类型：共性短板修复 #1（CS1 题面指令落实）
增量一句话：把 task.md 的原子约束拆成机读指令清单，成稿按清单逐条机审，违规即 error。
新增：scripts/instruction_audit.py → /app/work/instruction_checklist.json + /app/output/draft_audit.json；
      references/genre_profiles.md（体裁结构档案，被脚本读取）；validate_output.py 增 R8 读 draft_audit.json。
命中维度：实际效果·任务完成度(15) + 使用增益·效率增益(5) —— 指令清单同时减少评审核对与人工返工。
预期：机制真实增益 估 +9 → 兑现 +3
回归风险：R8 误报把合法成稿判 error → 用基线代理 case 回归（R1–R7 结果不变、R8 仅对真实违规报错）
回归用例：proxy normal（达标指令→R8 全过）+ degraded（异常路径不变）
回退：单 commit，可 revert
```

```
R2 → v2.0.1（基线 v1.0.1 / 89152 / 70.0 分）
类型：共性短板修复 #2（CS2 增益可验证）
增量一句话：新增"基础 Agent 失败模式拦截审计"产物，逐模式给出本次运行的拦截证据。
新增：scripts/gain_audit.py → /app/output/gain_audit.json；references/failure_modes.md（10 类失败模式定义，
      被脚本读取）；validate_output.py 增 R8 要求 gain_audit.json 存在。
命中维度：使用增益·质量增益(15) + 增益可验证性(5) —— 产物本身即"改善证据支撑质量"的可复核记录。
预期：机制真实增益 估 +9 → 兑现 +3
回归风险：审计结论措辞被误读为编造对照 → 每条只写"本次运行的拦截证据"，禁写未运行的基线数字；回归校验报告字段
回归用例：proxy normal + degraded（异常模式下审计仍出报告）
回退：单 commit，可 revert
```

```
R3 → v2.0.2（基线 v1.0.1 / 89152 / 70.0 分）
类型：单点机制 A（LIVE L3 深化：分句级支撑范围）
增量一句话：evidence.csv 增 support_span 列（摘录内支撑原句），机检 span ⊆ quote ⊆ 原文三层嵌套。
新增：scripts/span_verify.py → /app/output/span_report.json；validate_output.py 增 R8 三层嵌套校验。
命中维度：实际效果·结果可核验性(5) + 结果正确性(15) —— 复核者可直接对句，不需重读整段摘录。
预期：机制真实增益 估 +6 → 兑现 +2
回归风险：旧产物无 support_span 列被误判 → 列缺失按"未启用"跳过不报错，仅当列存在时强校验
回归用例：proxy normal（含 span → 全过）+ 基线旧产物（无 span 列 → 不报错）
回退：单 commit，可 revert
```

```
R4 → v2.0.3（基线 v1.0.1 / 89152 / 70.0 分）
类型：单点机制 B（L4 跨题迁移：数值溯源守恒）
增量一句话：机检成稿每个数值都能溯源到证据表摘录，无源数值即 error。
新增：scripts/number_trace.py → /app/output/number_trace.json；validate_output.py 增 R8 数值溯源校验
      （迁移自 学术语言润色/v1.0.0 的守恒检查思想，适配为"成稿→证据"方向）。
命中维度：实际效果·结果正确性(15) + 结果完整性(5) —— "数字来源可逐条回溯"是输出契约明示要求。
预期：机制真实增益 估 +6 → 兑现 +2
回归风险：数值写法差异（0.6% vs 0.6 %）误报 → 归一化（空白/全半角/千分位）后匹配，回归用例覆盖
回归用例：proxy normal（全部有源）+ 注入无源数值（必须报 error）
回退：单 commit，可 revert
```
