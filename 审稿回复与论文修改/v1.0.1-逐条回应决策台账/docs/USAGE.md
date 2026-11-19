# 使用说明（USAGE）

## 平台评测模式（主要用途）

平台把本目录安装到 `/skills/weekly-skill`，对固定案例运行 Agent。Agent 读到任务后按 SKILL.md 第 3 节步骤 0–8 执行即可；输入在 `/input/`，输出写 `/app/output/`。

## 独立复用模式

```bash
export SKILL=/path/to/v1.0.1-逐条回应决策台账
mkdir -p /tmp/work /tmp/output
python3 $SKILL/scripts/init_result.py --case case.json --out /tmp/output
python3 $SKILL/scripts/inspect_case.py --case case.json --task task.md --input-dir . --work /tmp/work
python3 $SKILL/scripts/parse_manuscript.py --work /tmp/work --file path/to/manuscript-baseline.md
python3 $SKILL/scripts/parse_comments.py --work /tmp/work --file path/to/reviewer-comments.md
# → 人工/Agent 复核 comments.json（重点核准 action_kind，它决定 audit 对症判据）
# → 撰写 dispositions.json（决策+回应+语气四档）与 edit_plan.json（锚点逐字抄录）
# → 如需补实验/数据/文献，写 evidence_checklist.json（EV# 条目）
python3 $SKILL/scripts/revision_engine.py --work /tmp/work --out /tmp/output
python3 $SKILL/scripts/response_engine.py --work /tmp/work --out /tmp/output --stage generate
# → 润色 response_letter.md（措辞可改，决策/E#/EV#/【待补】事实表述不可改）
python3 $SKILL/scripts/response_engine.py --work /tmp/work --out /tmp/output --stage audit
python3 $SKILL/scripts/verify_revision.py --work /tmp/work --out /tmp/output
python3 $SKILL/scripts/assemble_result.py --work /tmp/work --out /tmp/output \
  --case case.json --skill "revision-point-by-point-response v1.0.1" --status success
python3 $SKILL/scripts/validate_output.py --out /tmp/output --work /tmp/work
```

## 输入约定

- case.json：`case_id` + `output_contract`（字段列表，原样回填）；
- 稿件与意见文件名不限，inspect_case 按名称与内容双重嗅探；判错时用 `--file` 显式指定；
- response_engine 读取：work/comments.json、work/dispositions.json（必需），work/edit_report.json、work/edit_plan.json、work/evidence_checklist.json（可选，缺失时降级：EV# 无状态显示、op 状态记 ⚠）。

## 两个 stage 的分工

- `--stage generate`：台账 → 回复信草案。任何 disposition 改动后必须重新 generate，否则信件与台账脱节；
- `--stage audit`：回信质量闸门。exit 0=PASS / 1=FAIL；FAIL 明细在 `/app/output/audit_report.json`（off_topic_risk / tone_mismatch / weak_reject / hollow_accept / 红线命中行号与改写建议）。**手工改过回复信后必须重跑 audit**。

## 失败处理

任何脚本 FATAL → 读 stderr 原因；材料缺失 → result.json status=failed 并说明；锚点失败 → 修 quote 重跑；generate 标 ⚠ → 修 disposition 或锚点后重新 generate；audit FAIL → 按 audit_report.json 逐条修复重跑。详见 SKILL.md 第 4 节异常表。
