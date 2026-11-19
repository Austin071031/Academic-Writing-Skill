# 完整调用说明

## 输入

| 文件 | 说明 |
|-|-|
| /input/case.json | 案例标识与 output_contract |
| /input/task.md | 任务说明：目标文体、篇幅约束、保真要求 |
| /input/其他材料 | 源文（md/txt/tex/pdf/docx）、事实底稿、数据表 |

## 调用步骤

1. `init_result.py` 落盘骨架 result.json（防超时空手）。
2. `inspect_case.py` 解析出篇幅/源文候选/约束 → work/inspection.json。
3. `parse_source.py <源文>` → work/source.json（段落 pid、fact_index 事实清单、缩写、术语候选）。
4. **Agent 先写** work/retention_decisions.jsonl：每段一条 `{"source_pid","action":"保留|压缩|删除","reason"}`，
   覆盖全部含结论/比较/关键数据的段落；删除必须给 ≥4 字理由。
5. **Agent 再写** work/rewrite_draft.md：完整成稿；数字要么原样、要么走引擎认可的换算。
6. `align_rewrite.py` → work/alignment.json（源文-改写逐段对齐）。
7. `fidelity_engine.py check` → work/fidelity_report.json/.md（正向保真 + 反向溯源 + 图表编号；exit=0 才 PASS）。
8. `fidelity_engine.py ledger` → work/retention_ledger.json/.md（决定校验 + 人读台账；exit=0 才 OK）。
9. Agent 写 evidence_map/change_log/uncertainty/manual_confirmations。
10. 复制 rewrite.md / fidelity_report.md / retention_ledger.md 到 /app/output，
    `assemble_result.py` → `validate_output.py` → `render_previews.py`。

## 输出

| 文件 | 说明 |
|-|-|
| rewrite.md | 可编辑改写稿（主产物） |
| fidelity_report.md | 事实保真核验报告（人读，含换算式与问题清单） |
| retention_ledger.md | 内容取舍台账（每段 before/动作/理由/涉及事实） |
| result.json | case_id、status、output_contract 字段、产物清单 |
| preview.html | 全部 md 产物的渲染预览 |
| evidence_map / change_log / uncertainty（嵌于 result.json） | 来源映射、修改记录、待确认项 |

## 判定口径速查

| 判定 | 含义 | severity |
|-|-|-|
| verbatim | 原样出现（允许单位等价：5 nm/5纳米、85.3%/85.3％） | info |
| derived | 换算等价：百分比↔小数、四舍五入±1%、单位换算、端点重算（报告写换算式） | info |
| missing | 源文有而改写稿没有 | 同段含 compare/conclusion → critical，否则 warn |
| altered | 同量纲不同值（疑似篡改，如源文 85.3% 写成 89%） | 同上 |
| unverified | 改写稿出现源文无对应的数值 | critical |
| figure/table unknown | 改写稿引用了源文不存在的图/表编号 | critical |
| figure/table dropped | 源文被引图表在改写稿中消失 | warn |

## 自查方法

- `fidelity_engine.py check` exit=0 且无 critical；derived 的换算式逐条人工过一遍；
- `fidelity_engine.py ledger` exit=0；删除段落均在台账中写明理由与丢弃事实；
- alignment 的 dropped 与 retention_decisions 的"删除"一致；evidence_map 覆盖全部数据点。

## 限制

- 换算表只覆盖 nm/μm/mm/cm/km、Ω/kΩ/MΩ、mV/V/kV、mg/g/kg、μL/mL/L 及其中文别名；
  其他单位（MPa、℃ 等）只做原样比对。
- 遮蔽规则（年份/化学式/章节号）是启发式，可能放过或误伤个别边缘写法；
  被遮蔽项若构成实质性新事实仍需人工确认。
- "由 A 降至 B"端点重算只适用于百分比事实。
