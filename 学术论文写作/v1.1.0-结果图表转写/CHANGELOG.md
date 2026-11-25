# CHANGELOG

## v1.1.0（2026-11-23）
- 历史回顾：v1.0.0（attempt 88991，evaluation_error 未出分）管线过重、六类任务通吃导致主产物单薄；更早 attempt 71602 得 58.67，平台评语要求"更完整、真实推导的解"。
- 本版转向：聚焦题面"实验结果与图表转写"单一方向；管线减重为 2 脚本引擎 + 一段式收尾。
- 新增数值台账（facts_ledger）：CSV 行值+列统计+文本数值句子全带锚点，为写作唯一数字来源。
- 新增数字回写核验：未命中台账即 FAIL；【计算值：算式】豁免机制（推导值合规化）。
- 新增图注规范检查（引用必有注）与因果措辞警告（无检验禁"显著/导致"）。
- 提交：playground attempt 99604（challenge-308a6fdc，写作01｜学术论文写作）。
- 提交：playground attempt 106688（challenge-308a6fdc，写作01｜学术论文写作）。
  - 前次 attempt 99604 因 session_trace.jsonl 置于 skill 目录内触发预检（unsupported Skill resource），平台未扣次数；轨迹移出后重提通过预检。
