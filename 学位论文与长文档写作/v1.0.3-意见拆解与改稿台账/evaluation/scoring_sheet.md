# 自评打分表（scoring_sheet）

对应题面「持续修改：意见拆解与改稿落实台账（改得动）」。满分 100，目标 ≥80。

| 维度 | 分值 | 判据 | 证据文件 |
|-|-|-|-|
| 意见拆解完整性 | 20 | 工单每条意见都有修改项（rid/轮次/类型/目标文件），无臆造、无遗漏；无工单时 task.md 回退抽取并标注 | workorder_items.json |
| 定位与裁决 | 15 | 每条意见有 target_pids 或明确的无法定位原因；冲突意见检出并有裁决记录 | workorder_items.json（locate_top/conflicts） |
| 落实正确性 | 25 | 已落实条目文本确按意见修改且保留作者原意；新增内容可溯源材料；无"假落实" | revised/*.md、revision_ledger.json |
| 台账可说明性 | 15 | 每条意见有状态+理由+before/after 真实摘录+证据 pid；作者能看懂改了什么、为什么改 | revision_ledger.md |
| 可比较/可回退 | 10 | diff_report 为真实行级差异；work/original/ 备份齐全且与原件一致；version_report 含回退说明 | diff_report.md、original/、version_report.json |
| 诚实与异常处置 | 10 | 无法落实/待人工确认如实标注且原因具体；多轮覆盖有说明 | 台账、exceptions.json、uncertainty.json |
| 交付完整性 | 5 | result.json 含 output_contract 全部字段+case_id，validate PASS，预览生成 | result.json、validate 输出 |

## 扣分红线（触及即该维度 0 分）

- before/after 不是真实文本（编造摘录）；
- status=已落实 但 revised 文本与原件无对应差异；
- 改写 /input 原件或没有 work/original/ 备份；
- agent_edits.json 漏条且无"待人工确认"兜底。

## 自测记录（v1.0.3 合成案例）

- 正例（R1/R2）：拆解 2/2、定位 2/2、落实 2/2、台账 before/after 真实、
  diff 真实、备份与原件 diff 一致、validate PASS → 自评 97（交付命名细节扣 3）。
- 负例：目标文件缺失 → 无法落实+原因 ✓；补充/删除同 pid → conflict 检出 ✓。
