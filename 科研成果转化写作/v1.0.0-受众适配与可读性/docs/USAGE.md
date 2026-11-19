# 完整调用说明

## 输入

| 文件 | 说明 |
|-|-|
| /input/case.json | 案例标识与 output_contract |
| /input/task.md | 任务说明：目标受众、文体、篇幅约束 |
| /input/其他材料 | 源文（md/txt/tex/pdf/docx）、事实底稿、数据表 |

## 调用步骤

1. `init_result.py` 落盘骨架 result.json。
2. `inspect_case.py` 解析出受众/文体/篇幅/源文候选 → work/inspection.json。
3. `parse_source.py <源文>` → work/source.json（段落 pid、事实清单、缩写、术语候选）。
4. `audience_engine.py profile` → work/audience_profile.json（术语处置计划+写作目标）。
5. Agent 按画像撰写 work/rewrite_draft.md。
6. `align_rewrite.py` + `audience_engine.py check` → 对齐与可读性核查（exit=0 才达标）。
7. Agent 写 evidence_map/change_log/uncertainty/manual_confirmations。
8. 复制改写稿与报告到 /app/output，`assemble_result.py` → `validate_output.py` → `render_previews.py`。

## 输出

| 文件 | 说明 |
|-|-|
| rewrite.md | 可编辑改写稿（主产物） |
| readability_report.md | 可读性核查报告（人读） |
| result.json | case_id、status、output_contract 字段、产物清单 |
| preview.html | 全部 md 产物的渲染预览 |
| evidence_map / change_log / uncertainty（嵌于 result.json） | 来源映射、修改记录、待确认项 |

## 自查方法

- `audience_engine.py check` exit=0 且无 critical；
- alignment 无"非故意" dropped；
- evidence_map 覆盖全部数据点；status 与实际完成度一致。

## 限制

- 可读性阈值为工程经验值；专业深度取舍仍需 Agent/作者判断。
- 对齐为字符 2-gram 包含度启发式，大改写的段落可能判 partial，需人工确认。
