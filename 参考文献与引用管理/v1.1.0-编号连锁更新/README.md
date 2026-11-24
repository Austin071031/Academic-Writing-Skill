# citation-renumber-chain｜参考文献编号连锁更新（编得顺）

对顺序编码制（numeric / GB/T 7714 顺序编码）稿件执行**引用条目级编辑**时，保证正文
引用、文末列表、图注、表注、附录、脚注中的编号全部同步：连续、无悬空、无缺口、样式统一。

## 用途

- 任务书要求**删除**若干文献、**调整**文末列表顺序、把文献库中**已有条目插入**列表、
  两章**合并**后条目去重（merge）、增删段落导致引用集合变化——本 Skill 把这类编辑
  编译成全确定性的编号连锁更新。
- Agent 只写语义化操作 `work/edit_ops.json`；编号重排一律由脚本完成，Agent 禁止手改
  正文数字（本 Skill 的第一红线）。

## 安装

把本目录整体复制为评测环境的 `/skills/weekly-skill` 即可（纯 Python3 标准库，
scripts/ 内含 8 个共享核心脚本 + 1 个专属 `renumber_plan.py`）。

## 快速开始（Agent 视角）

```bash
# Phase 0-1: 初始化 + 解析
python3 /skills/weekly-skill/scripts/init_result.py --case /input/case.json --out /app/output
python3 /skills/weekly-skill/scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 /skills/weekly-skill/scripts/parse_manuscript.py <稿件> --work /app/work
python3 /skills/weekly-skill/scripts/parse_library.py <文献库...> --work /app/work

# Phase 2: Agent 写编辑操作（唯一的手工判断产物）
# work/edit_ops.json ← [{"op":"delete","ref_id":"R004","note":"任务书：删除该专著"}]

# Phase 3: 引擎连锁更新 + 不变量终检
python3 /skills/weekly-skill/scripts/renumber_plan.py --work /app/work --out /app/output \
  --engine /skills/weekly-skill/scripts/cite_engine.py
# 关注 stdout 末行 INVARIANTS: PASS/FAIL 与 output/renumber_report.md 的悬空清单

# Phase 5: 收尾
python3 /skills/weekly-skill/scripts/assemble_result.py --work /app/work --out /app/output \
  --skill "citation-renumber-chain v2.0.0" --status success
python3 /skills/weekly-skill/scripts/validate_output.py --out /app/output --expect-status success
python3 /skills/weekly-skill/scripts/render_previews.py --out /app/output
```

## 边界

- 只处理**编号连锁**：不为被删条目找替代品、不验证文献真实性、不做内容润色。
- 著者-出版年稿件不做数字重排，仅检查列表排序 + 标注 stale 条目（报告说明）。
- 悬空引用（删了还被引）是流程内正常 intermediate 状态：引擎 FAIL 并列出段落，
  Agent 改写句子后重跑，直到 PASS；不自动删句子。
- 详见 `docs/USAGE.md`、`references/` 下方法文档与 `evaluation/` 下自测材料。
