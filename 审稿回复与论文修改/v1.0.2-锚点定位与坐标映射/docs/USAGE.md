# 使用说明（USAGE）

## 平台评测模式（主要用途）

平台把本目录安装到 `/skills/weekly-skill`，对固定案例运行 Agent。Agent 读到任务后按 SKILL.md 第 3 节步骤 0–8 执行即可；输入在 `/input/`，输出写 `/app/output/`。

## 独立复用模式

```bash
export SKILL=/path/to/v1.0.2-锚点定位与坐标映射
mkdir -p /tmp/work /tmp/output
python3 $SKILL/scripts/init_result.py --case case.json --out /tmp/output
python3 $SKILL/scripts/inspect_case.py --case case.json --task task.md --input-dir . --work /tmp/work
python3 $SKILL/scripts/parse_manuscript.py --work /tmp/work --file path/to/manuscript-baseline.md
python3 $SKILL/scripts/parse_comments.py --work /tmp/work --file path/to/reviewer-comments.md
# → 人工/Agent 复核 comments.json，撰写 dispositions.json 与 edit_plan.json
python3 $SKILL/scripts/revision_engine.py --work /tmp/work --out /tmp/output
python3 $SKILL/scripts/anchor_engine.py --work /tmp/work --out /tmp/output   # 首跑：生成 location_table.md（无回信则跳过声明核验）
# → 按 templates/ 与 references/anchor_rules.md 撰写 response_letter.md 等
python3 $SKILL/scripts/anchor_engine.py --work /tmp/work --out /tmp/output   # 复跑：核验回复信定位声明，exit 1 = 有不可核对声明
python3 $SKILL/scripts/verify_revision.py --work /tmp/work --out /tmp/output
python3 $SKILL/scripts/assemble_result.py --work /tmp/work --out /tmp/output \
  --case case.json --skill "revision-anchor-localization v1.0.2" --status success
python3 $SKILL/scripts/validate_output.py --out /tmp/output --work /tmp/work
```

## 输入约定

- case.json：`case_id` + `output_contract`（字段列表，原样回填）；
- 稿件与意见文件名不限，inspect_case 按名称与内容双重嗅探；判错时用 `--file` 显式指定；
- `--baseline` 可显式指定基线路径；缺省取 structure.json 的 `source_file`。基线不可读时引擎降级为 structure 段落模式并在产物中注明。

## 失败处理

- anchor_engine exit 1：读 stderr 的 `[FAIL]` 行与 `work/anchor_map.json` 的 `letter_claims.unresolvable_claims`，逐条修复（悬空 E# 换成已 applied 编号；引文逐字抄自修订稿；行号/段坐标以 location_table.md 为准）后重跑；
- revision_engine exit 2：锚点问题，修 quote 或 para_id 后先重跑 revision_engine，再重跑 anchor_engine（顺序不可颠倒，否则定位基于旧修订稿）；
- 回复信任何手改后必须重跑 anchor_engine；
- 材料缺失 → result.json status=failed 并说明。详见 SKILL.md 第 4 节异常表。
