# 完整调用说明

## 输入

| 文件 | 说明 |
|-|-|
| /input/case.json | 案例标识与 output_contract |
| /input/task.md | 任务说明：目标受众、文体（可能多份产物）、篇幅约束 |
| /input/其他材料 | 源文（md/txt/tex/pdf/docx）、事实底稿、数据表 |

## 调用步骤

1. `init_result.py` 落盘骨架 result.json。
2. `inspect_case.py` 解析受众/文体/篇幅/源文候选 → work/inspection.json。
3. `parse_source.py <源文>` → work/source.json（段落 pid、事实清单、缩写、术语候选）。
4. `terminology_engine.py candidates --source work/source.json --work work` → work/term_table_draft.json。
5. **Agent 审定草稿**（增删改条目、确认 canonical/variants/first_expand/cross_genre），
   另存为 `work/term_table.json`。
6. Agent 按术语表撰写 `work/rewrite_draft.md`（多产物再写 work/briefing.md 等）。
7. `align_rewrite.py` + `terminology_engine.py audit --table work/term_table.json --rewrite work/rewrite_draft.md [--more 其他产物 ...] --work work`：critical 修复重跑至 exit=0。
8. Agent 写 evidence_map/change_log/uncertainty/manual_confirmations，并把 term_table.json
   转写为人读 `work/term_table.md`。
9. 复制 rewrite.md / term_table.md / terminology_audit.md 到 /app/output，
   `assemble_result.py` → `validate_output.py` → `render_previews.py`。

## 输出

| 文件 | 说明 |
|-|-|
| rewrite.md | 可编辑改写稿（主产物，术语全表锁定） |
| term_table.md | 人读锁定术语表（canonical/variants/跨文体策略） |
| terminology_audit.md | 术语一致性审计报告（逐条定位 file:rpid） |
| result.json | case_id、status、output_contract 字段、产物清单、台账 |
| preview.html | 全部 md 产物的渲染预览 |

## 自查方法

- `terminology_engine.py audit` exit=0 且无 critical；warn 逐条处置或改表重跑；
- 术语表每条 canonical 在源文有据（evidence_map 覆盖）；
- alignment 无"非故意" dropped；status 与实际完成度一致。

## 限制

- 异写判据为相似度阈值（0.70）启发式，机选草稿必须经 Agent/作者审定，误判在 note 标注；
- 跨文件一致性按"各产物主导说法"判定，个别修辞性变体需人工确认；
- 对齐为字符 2-gram 包含度启发式，大改写段落可能判 partial，需人工确认。
