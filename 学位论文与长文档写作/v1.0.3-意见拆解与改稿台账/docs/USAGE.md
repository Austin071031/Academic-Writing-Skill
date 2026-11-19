# 使用说明（USAGE）

## 1. 安装与运行环境

评测方将本目录安装为 `/skills/weekly-skill`。运行环境：Python 3（仅标准库），
输入 `/input`，工作 `/app/work`，产物 `/app/output`。预算约 64 次模型请求 / 900 秒。

## 2. 命令一览

| 阶段 | 命令 | 产出 |
|-|-|-|
| Phase 0 | `init_result.py --case /input/case.json --out /app/output` | 骨架 result.json |
| Phase 0 | `inspect_case.py --case … --task … --input-dir /input --work /app/work` | work/inspection.json（含 workorder_files） |
| Phase 1 | `parse_chapters.py <章节/材料文件…> --work /app/work` | work/chapters.json（稳定 pid） |
| Phase 1 | `revision_engine.py parse [--workorder W] [--task T] --work /app/work` | work/workorder_items.json |
| Phase 2 | `revision_engine.py locate --work /app/work` | 写回 target_pids / conflicts |
| Phase 3 | （Agent 写 agent_edits.json）`revision_engine.py apply --work /app/work` | work/original/、work/revised/、revision_ledger.json/.md、diff_report.md |
| Phase 4 | `parse_chapters.py /app/work/revised/*.md --out-name chapters_revised.json` + 重跑 locate；`revision_engine.py version --work /app/work` | work/version_report.json |
| Phase 5 | `assemble_result.py … --skill "longdoc-revision-ledger v1.0.3" --status …` → `validate_output.py …` → `render_previews.py …` | /app/output/result.json 等 |

所有 revision_engine 子命令的 `--chapters/--items/--edits` 缺省指向 `--work` 下同名文件。

## 3. 关键文件格式

### workorder_items.json（parse 产出 / locate 写回）

```json
{"source": "/input/organizer-edit-workorder.json", "note": null, "n_items": 2,
 "items": [{"rid": "R1", "round": 1, "target_file": "ch1_intro.md", "type": "补充",
            "content": "……意见原文……", "status": "pending",
            "target_pids": ["C01-S001-P003"], "locate_top": [{"pid": "…", "overlap": 12, "excerpt": "…"}]}],
 "conflicts": [{"pid": "C02-S001-P002", "rids": ["R4", "R5"], "types": ["补充", "删除"], "reason": "…"}]}
```

`status` 取值：`pending` →（apply 后）`已落实` / `部分落实` / `无法落实` / `待人工确认`。

### agent_edits.json（Agent 手写，每条 pending 意见必须有一条）

```json
[{"rid": "R1", "action": "edit", "target_pid": "C01-S001-P003", "mode": "replace",
  "new_text": "完整替换段文字", "reason": "为什么这样改"},
 {"rid": "R2", "action": "skip",  "reason": "无法落实的原因（如实写）"},
 {"rid": "R3", "action": "defer", "reason": "需人工确认的事项"}]
```

- `action=edit`：`new_text` 必填；`mode` = `replace`（默认，整段替换 target_pid 原文）/
  `append_after`（插到 target_pid 之后）/ `append_end`（追加到目标文件末尾）。
- `target_pid` 可省略：缺省取 locate 的 top1；都找不到时引擎按关键词在文件内模糊定位，
  仍找不到 → 无法落实（拒绝臆改）。

### revision_ledger.json / .md（落实台账）

每条意见一条记录：`{rid, round, target_file, type, content, action, status, reason,
before, after, evidence_pid, mode}`。before/after 均为真实文本摘录（≤220 字）。

### version_report.json（按轮汇总，assemble_result 自动收录进 result.json）

```json
{"n_opinions": 2,
 "rounds": [{"round": 1, "n_opinions": 2, "n_done": 2, "n_partial": 0,
             "n_unable": 0, "n_manual": 0, "n_pending": 0, "unresolved": []}],
 "conflicts": [...],
 "rollback": {"backup_dir": "work/original/", "backed_up_files": ["ch1_intro.md"],
              "how_to": "回退：用 work/original/<文件> 覆盖 ……"}}
```

## 4. 回退操作

1. 单条回退：查 `diff_report.md` 确认差异 → 用 `work/original/<文件>` 覆盖
   `work/revised/` 同名文件后重新执行需要的修改。
2. 整体回退：`work/original/` 是全部改动前原件的逐字节副本（shutil.copy2），
   直接覆盖回章节源目录即恢复到改前状态。
3. 回退后重跑 `apply`（引擎幂等：备份只建一次，revised 从备份重建需先删除
   revised 对应文件）。

## 5. 与其他脚本的配合

- `evidence_map.json`：每条已落实意见写 `{rid, claim, evidence, pid}`，
  validate 要求 status=success 时非空。
- `uncertainty.json` / `exceptions.json` / `stats.json`：均为
  `[{item, reason, severity}]` 或自由 JSON，assemble_result 自动收录。
