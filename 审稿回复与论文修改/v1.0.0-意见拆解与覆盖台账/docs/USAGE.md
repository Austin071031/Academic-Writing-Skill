# 使用说明（USAGE）

## 平台评测模式（主要用途）

平台把本目录安装到 `/skills/weekly-skill`，对固定案例运行 Agent。Agent 读到任务后按 SKILL.md 第 3 节步骤 0–8 执行即可；输入在 `/input/`，输出写 `/app/output/`。

## 独立复用模式

```bash
export SKILL=/path/to/v1.0.0-意见拆解与覆盖台账
mkdir -p /tmp/work /tmp/output
python3 $SKILL/scripts/init_result.py --case case.json --out /tmp/output
python3 $SKILL/scripts/inspect_case.py --case case.json --task task.md --input-dir . --work /tmp/work
python3 $SKILL/scripts/parse_manuscript.py --work /tmp/work --file path/to/manuscript-baseline.md
python3 $SKILL/scripts/parse_comments.py --work /tmp/work --file path/to/reviewer-comments.md
python3 $SKILL/scripts/decompose_engine.py --work /tmp/work --out /tmp/output --stage first
# → 人工/Agent 复核 comments.json，撰写 dispositions.json 与 edit_plan.json
python3 $SKILL/scripts/revision_engine.py --work /tmp/work --out /tmp/output
# → 撰写 response_letter.md / edit_locations.md / evidence_checklist.md 等
python3 $SKILL/scripts/decompose_engine.py --work /tmp/work --out /tmp/output --stage audit
python3 $SKILL/scripts/verify_revision.py --work /tmp/work --out /tmp/output
python3 $SKILL/scripts/assemble_result.py --work /tmp/work --out /tmp/output \
  --case case.json --skill "revision-comment-decomposition v1.0.0" --status success
python3 $SKILL/scripts/validate_output.py --out /tmp/output --work /tmp/work
```

## 输入约定

- case.json：`case_id` + `output_contract`（字段列表，原样回填）；
- 稿件与意见文件名不限，inspect_case 按名称与内容双重嗅探；判错时用 `--file` 显式指定。

## 失败处理

任何脚本 FATAL → 读 stderr 原因；材料缺失 → result.json status=failed 并说明；锚点失败 → 修 quote 重跑；覆盖缺口 → 补 dispositions 重跑 audit。详见 SKILL.md 第 4 节异常表。
