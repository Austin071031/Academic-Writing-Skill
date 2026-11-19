# longdoc-revision-ledger v1.0.3

学位论文与长文档写作方向 Skill —— **持续修改：意见拆解与改稿落实台账（改得动）**。

把导师/评审意见（组织方工单 `organizer-edit-workorder.json`）拆成可执行修改项，
逐条定位到段落、落实文本修改、记录落实台账；修改可回退（原件备份）、可比较（diff）、
可说明（逐条 before/after + 理由）。无法落实的意见如实标注原因，绝不假装完成。

## 目录结构

```
SKILL.md                     # 工作流定义（Phase 0-5、三条红线、异常处置表）
scripts/
  revision_engine.py         # 本版本引擎：parse / locate / apply / version
  init_result.py             # 共享：防超时空手的 result.json 骨架
  inspect_case.py            # 共享：输入盘点（识别 workorder_files）
  parse_chapters.py          # 共享：章节解析 + 稳定段落 pid
  assemble_result.py         # 共享：汇总 result.json（自动收录 version_report.json）
  validate_output.py         # 共享：交付闸门
  render_previews.py         # 共享：HTML 预览
  parse_library.py / cite_engine.py  # 共享：文献（本版本可不用，保留）
docs/USAGE.md                # 使用说明与文件格式
references/revision_rules.md # 意见分类与落实判据
references/failure_modes.md  # 典型失败模式
examples/minimal_example.md  # 最小端到端示例（标注）
evaluation/scoring_sheet.md  # 自评打分表
evaluation/test_texts.md     # 合成测试文本（标注合成）
CHANGELOG.md
GITHUB_URL.txt
```

## 快速开始

```bash
python3 scripts/init_result.py --case /input/case.json --out /app/output
python3 scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 scripts/parse_chapters.py /input/chapters/*.md --work /app/work
python3 scripts/revision_engine.py parse --workorder /input/organizer-edit-workorder.json --work /app/work
python3 scripts/revision_engine.py locate --work /app/work
# Agent 写 /app/work/agent_edits.json 后：
python3 scripts/revision_engine.py apply --work /app/work
python3 scripts/revision_engine.py version --work /app/work
python3 scripts/assemble_result.py --work /app/work --out /app/output --skill "longdoc-revision-ledger v1.0.3" --status success
python3 scripts/validate_output.py --out /app/output --work /app/work
```

详见 SKILL.md 与 docs/USAGE.md。
