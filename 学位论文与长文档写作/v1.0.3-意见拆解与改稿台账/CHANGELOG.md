# CHANGELOG

## v1.0.3（当前版本）

- 新增 `scripts/revision_engine.py`（纯标准库），四个子命令：
  - `parse`：拆解组织方工单（兼容 rounds/opinions/items/comments/edits 与
    id/target/type/content/opinion 多种键名）；无工单时从 task.md 规则抽取意见行
    （含 修改/补充/删除/改写/调整/统一/检查 等动词），类型自动归类
    （补充/删除/改写/结构调整/格式/引用/其他）。
  - `locate`：target_file 限定 + content 关键词 2-gram 重叠 top3 定位候选段落 pid；
    冲突检测（两条意见同 pid 且类型相反 补充 vs 删除 → conflict 标记供 Agent 裁决）。
  - `apply`：执行 `work/agent_edits.json`（edit/skip/defer，支持 replace/append_after/
    append_end）；原件自动备份 `work/original/`，修改只发生在 `work/revised/`；
    生成 `revision_ledger.json/.md`（已落实/部分落实/无法落实+原因/待人工确认，
    含真实 before/after 摘录与证据 pid）与 `diff_report.md`（difflib 行级差异）。
  - `version`：按 round 汇总落实率与未落实原因，写回退说明（备份路径+回退方法），
    追加 change_log → `work/version_report.json`（assemble_result 自动收录）。
- SKILL.md：Phase 0-5 流程、三条红线（不臆造意见内容/不假装落实/不覆盖原件先备份）、
  10 类异常处置表、预算兜底（批量 defer + 保底交付）。
- 复用 shared-core 全部脚本（接口未改）。
- 配套：docs/USAGE.md、references/revision_rules.md、references/failure_modes.md、
  examples/minimal_example.md、evaluation/scoring_sheet.md、evaluation/test_texts.md。
- 端到端测试：合成案例（R1 补充两步烧结区别 / R2 改写 EIS 测试条件）全流程
  validate PASS；负例覆盖"目标文件缺失→无法落实+原因"与"相反意见同 pid→conflict 检出"。
