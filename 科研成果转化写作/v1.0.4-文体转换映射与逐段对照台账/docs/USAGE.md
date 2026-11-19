# 完整调用说明

## 输入

| 文件 | 说明 |
|-|-|
| /input/case.json | 案例标识与 output_contract |
| /input/task.md | 任务说明：目标文体、受众、篇幅约束 |
| /input/其他材料 | 源文（md/txt/tex/pdf/docx）、事实底稿、数据表 |

## 调用步骤

1. `init_result.py` 落盘骨架 result.json。
2. `inspect_case.py` 解析出文体/受众/篇幅/源文候选 → work/inspection.json。
3. `parse_source.py <源文>` → work/source.json（段落 pid、事实清单、缩写、术语候选）。
4. `genre_engine.py map` → work/genre_mapping.json（文体模板要素 + 要素→源文段落映射 + 缺失要素）。
5. Agent 按模板要素撰写 work/rewrite_draft.md，**同时**逐段写 work/change_reasons.jsonl
   （每个改写段落一条理由：保留/压缩/改写/新增-过渡；每个删除的源文段落一条「删除」理由）。
6. `align_rewrite.py` → work/alignment.json（links/dropped/added）。
7. `genre_engine.py ledger` → work/change_ledger.json + work/traceability_report.md；
   critical 必须修复后重跑，exit=0 方可交付。
8. Agent 写 evidence_map/change_log/uncertainty/manual_confirmations。
9. 复制 rewrite.md、traceability_report.md、change_ledger.json 到 /app/output，
   `assemble_result.py` → `validate_output.py` → `render_previews.py`。

## change_reasons.jsonl 格式

```jsonl
{"rpid":"R002","source_pid":"S001-P003","action":"改写","reason":"……"}
{"rpid":"R006","action":"新增-过渡","reason":"……"}
{"source_pid":"S001-P007","action":"删除","reason":"……"}
```

- rpid：改写稿段落按空行分块的序号（R001 起，与 align_rewrite 一致）；
- action 取值：`保留 | 压缩 | 改写 | 新增-过渡 | 删除`。

## 输出

| 文件 | 说明 |
|-|-|
| rewrite.md | 可编辑改写稿（主产物，按目标文体模板组织） |
| traceability_report.md | 逐段对照台账（人读两表：源文→改写覆盖表、改写→源文溯源表+问题清单） |
| change_ledger.json | 台账机读版（verdict/issues/source_coverage/rewrite_trace/stats） |
| result.json | case_id、status、output_contract 字段、产物清单 |
| preview.html | 全部 md 产物的渲染预览 |
| evidence_map / change_log / uncertainty（嵌于 result.json） | 来源映射、修改记录、待确认项 |

## 核查判定

| 级别 | 类型 | 含义 |
|-|-|-|
| critical | dropped_without_reason | 源文段落未被覆盖且 change_reasons.jsonl 无「删除」理由 |
| warn | added_without_reason / added_action_mismatch | 新增段落未标「新增-过渡」 |
| warn | added_contains_number | 新增段落含数值+单位，需核对是否源外事实 |
| warn | action_contradiction | 理由动作与引擎对齐结果矛盾（如「保留」但 sim<0.12） |

verdict=PASS（无 critical）时 ledger exit 0；否则 exit 2。

## 自查方法

- `genre_engine.py ledger` exit=0 且无 critical；
- traceability_report.md 表一每行源文段落都有去向（覆盖或删除+理由），表二每个改写段落都有来源；
- 缺失要素在成稿中标注「源文未提供」；status 与实际完成度一致。

## 限制

- 要素映射为关键词启发式，跨要素复用的段落会同时出现在多个要素下，需 Agent 取舍；
- 对齐为字符 2-gram 包含度启发式，彻底重述的段落可能判 partial/added，需人工结合台账确认；
- ledger 只核查"可追溯性"，事实逐值核验见 transfer-fact-fidelity 版本。
