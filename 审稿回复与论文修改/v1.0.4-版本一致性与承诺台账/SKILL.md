---
name: revision-version-consistency
description: 审稿回复与论文修改的"版本一致性"方向技能。当任务给出基线稿件与审稿意见，要求交付修订稿与逐条回复信（尤其多轮返修场景）时使用。核心能力：维护意见、改动与承诺的对应台账，对基线与修订稿做真实行级 diff，把回复信声称的每处修改、每个编辑操作与差异区域三方对账，保证回复信引用的位置与当前稿件版本一一对齐；多轮返修中嗅探上一轮回复信，抽取承诺句式逐条核对兑现状态，使上一轮承诺可追踪兑现。适用于受控返修演练与真实返修的一致性核验阶段。
---

# 审稿回复与论文修改：版本一致性与承诺台账

## 1. 用途与适用条件

本 Skill 解决返修中"对得上"维度的四类典型失败：**声称已改但无实际差异**（回复信说改了，修订稿却没变）、**改了但没声明**（修订稿多出回复信未交代的改动，审稿人无法溯源）、**引用漂移**（回复信引用的 E#/行号指向旧版本，与当前稿件对不上）、**跨轮承诺落空**（第一轮承诺"下一轮补充对比表"，第二轮交付时无人核对是否兑现）。

核心原则：

1. **三方对账**：声称（回复信引用 + 处置决策）、操作（edit_report 的 applied ops）、差异（基线↔修订稿的真实行级 diff regions）必须两两闭合；任一方落不到差异区域内部即判 FAIL，而非只在全稿里找子串。
2. **差异为唯一事实源**：以 difflib 行级 opcodes 计算 diff region；纯空行/空白差异按噪音豁免，其余每个区域必须被编辑操作认领，未认领即 WARN 交人工确认。
3. **承诺可追踪**：多轮返修时嗅探历史回复文件，抽取承诺句式（将/会/下一步/下一轮/we will 等），逐条与本轮处置和编辑操作做关键词重叠核对，兑现状态写入台账。
4. **诚实边界**：只修订指定基线；无法补做的内容用【待补：…】占位；占位兑现的承诺只记"部分兑现"，不记"已兑现"；核验不过不得报 success。

适用条件：输入含可读的基线稿件与审稿意见；多轮场景下 `/input/materials/` 可能另含上一轮回复信或历史版本文件。

## 2. 输入与输出

输入：`/input/case.json`（case_id、output_contract，可能含 `constraints.round` 或 `revision_round` 轮次信息）、`/input/task.md`、`/input/` 材料（典型为 `materials/manuscript-baseline.md` 与 `materials/reviewer-comments.md`；多轮场景可能含上一轮回复信/历史版本，名称由本 Skill 嗅探判定）。

输出（写入 `/app/output/`）：

| 文件 | 内容 |
|-|-|
| `result.json` | output_contract 全字段 + case_id + status + sources + uncertainty + change_log |
| `revised_manuscript.md` | 可编辑修订稿（锚点编辑真实应用后的全文） |
| `response_letter.md` | 逐条回复信草案（每条含决策与 E# 修改指涉） |
| `edit_locations.md` | 修改定位表（操作→锚点→修订稿行号） |
| `evidence_checklist.md` | 未到位证据清单 |
| **`consistency_report.md`** | **版本一致性对账报告：差异区域清单 + 三方对账 + 承诺台账** |
| **`revision_ledger.json`** | **多轮承诺台账（承诺摘录/来源/兑现状态/对应 sub_id 与 op）** |
| `verification.json` | 五重交叉核验结果 |

中间产物：`/app/work/consistency.json`（机器可读对账结果）及其余 work/*.json（契约见 `references/schemas.md`）。

## 3. 工作流程

约定：`$SKILL=/skills/weekly-skill`。全程只依赖 Python3 标准库。

### 步骤 0：立即落盘骨架（防超时空手）

```bash
python3 $SKILL/scripts/init_result.py --case /input/case.json --out /app/output
```

### 步骤 1：侦察输入

```bash
python3 $SKILL/scripts/inspect_case.py --case /input/case.json --task /input/task.md \
  --input-dir /input --work /app/work
```

读 `/app/work/inspection.json` 确认基线与意见文件候选；判错时后续脚本用 `--file` 显式指定。issues 记入 `/app/work/exceptions.json`。

### 步骤 2：解析基线结构 + 嗅探历史版本

```bash
python3 $SKILL/scripts/parse_manuscript.py --work /app/work
```

产出 `structure.json`（含 `source_file` 基线路径，是后续 diff 的事实源）。

**多轮场景额外动作**：读 case.json 的 `constraints.round` / `revision_round` 确认当前轮次；在 `/input/materials/` 与 `/input/` 下查找文件名含 response|reply|回复|rebuttal|round|r1 的历史回复文件。找到则通读一遍，人工标记其中的承诺句（"我们将在下一轮……"），供步骤 7 台账核对参考；找不到则在不确定性中注明"无历史承诺"。命名约定见 `references/consistency_rules.md` 第 5 节。

### 步骤 3：解析意见

```bash
python3 $SKILL/scripts/parse_comments.py --work /app/work
```

由你（Agent）复核 `comments.json`：补拆漏掉的子要求、合并过碎拆分、修正类型初判。每条意见必须能追到子要求级 ID，这是回复信引用不发生漂移的前提。

### 步骤 4：制定处置决策与编辑计划

写 `/app/work/dispositions.json` 与 `/app/work/edit_plan.json`（schema 见 `references/schemas.md`）。一致性视角的三条纪律：

- 采纳/部分采纳且声称改了正文 → `edit_ops` 必须非空，不允许"口头采纳"；
- 每个 op 的 `new_text` 即未来 diff 的落点，回复信引用它之前先确认它能真实应用；
- 若嗅探到上一轮承诺，逐条在本轮 dispositions 中安排兑现位置（op 或证据条目），或在 response 中说明无法兑现的原因。

### 步骤 5：应用编辑

```bash
python3 $SKILL/scripts/revision_engine.py --work /app/work --out /app/output
```

exit=2 表示有失败锚点：读 `work/edit_report.json` 的 reason，修正 quote 重跑。**锚点失败的 op 不得留在回复信里声称已改**——它不会产生任何 diff region，步骤 7 必判 FAIL。

### 步骤 6：撰写回复信与配套产物

按 `templates/revision_ledger.md` 的引用规范写 `/app/output/response_letter.md`：每条处置引用 E#，E# 只引用 edit_report 中 status=applied 的操作；写 `edit_locations.md`、`evidence_checklist.md`、`work/change_log.json`、`uncertainty.json`、`manual_confirmations.json`、`stats.json`。

### 步骤 7：版本一致性对账 + 交叉核验

```bash
python3 $SKILL/scripts/consistency_engine.py --work /app/work --out /app/output \
  --case /input/case.json --input-dir /input
python3 $SKILL/scripts/verify_revision.py --work /app/work --out /app/output
```

consistency_engine 做五类检查（规则细节见 `references/consistency_rules.md`）：

- **A. 操作→差异**：每个 applied op 的 new_text_head 必须落在某个 diff region **内部**（强校验，非全稿子串）；找不到 → FAIL"声称已改但无实际差异"；
- **B. 差异→操作**：每个非豁免 diff region 必须被 op 认领；未认领 → WARN"存在未声明的改动"，列出供人工确认；
- **C. 承诺兑现**：采纳/部分采纳但 edit_ops 与 evidence 均空 → FAIL"承诺未兑现"；
- **D. 回复信引用**：每个 E# 必须存在、applied、落在 diff region；
- **E. 承诺台账**：嗅探历史回复文件，抽取承诺句逐条核对兑现（已兑现/部分兑现/未兑现/无法判定），写入 `revision_ledger.json` 与对账报告第 3 节。

exit=1 存在 FAIL 项：逐项修复后重跑至 exit=0；WARN 项逐条人工确认，确认结论写入 `work/manual_confirmations.json`；无法判定的承诺写入 `work/uncertainty.json`。verify_revision 五重核验仍需 PASS。

### 步骤 8：汇总交付

```bash
python3 $SKILL/scripts/assemble_result.py --work /app/work --out /app/output \
  --case /input/case.json --skill "revision-version-consistency v1.0.4" --status success
python3 $SKILL/scripts/validate_output.py --out /app/output --work /app/work
```

validate PASS 后结束；FAIL 按提示修复或如实降级 status。

## 4. 异常处理

| 情况 | 处置 |
|-|-|
| 找不到意见文件或基线文件 | inspect issues 记录；status=failed 并说明缺什么，不编造内容 |
| 上轮回复信缺失（round>1 但嗅探不到历史文件） | 台账注明"未嗅探到历史回复文件，按无历史承诺处理"+ WARN；不虚构历史承诺 |
| 重排/格式噪音导致未认领 diff region | WARN 列出区域行号与内容头；人工确认后写入 manual_confirmations；纯空白差异引擎自动豁免 |
| 承诺无法判定（承诺句过短/关键词不足） | 台账记"无法判定"+ WARN；列入 uncertainty，回复信中主动说明兑现情况 |
| 上一轮承诺本轮确实未兑现 | 不得装作兑现；台账如实记"未兑现"，回复信说明原因与新计划，status 降 partial |
| op 声称 applied 但落不进任何 diff region | FAIL"声称已改但无实际差异"；检查是否编辑被空白归一化吞掉或写错了文件，修复后重跑 |
| 回复信引用了不存在/未应用的 E# | FAIL；改为引用真实 applied 的 op 或删除该指涉 |
| 锚点多次出现或找不到 | 按 revision_engine reason 修正 quote / 指定 para_id 重跑；不得谎称已改 |
| 承诺以【待补】占位兑现 | 台账最多记"部分兑现"；证据清单保留待补条目，不得记"已兑现" |
| 重复运行 | 脚本幂等；consistency_engine 每次全量重算 diff 与台账，直接重跑即可 |

## 5. 最小调用示例（示意，非真实案例答案）

输入（示意）：case.json 含 `{"case_id":"demo","constraints":{"round":2},"output_contract":[...]}`；materials 含基线、意见与 `prev_response_round1.md`（含承诺句"我们将在下一轮补充对比表"）。

调用：步骤 0→8 顺序执行；revision_engine 应用 5/5；consistency_engine 计算得 3 个 diff region、5 个 op 全部落点、嗅探到 1 条历史承诺并匹配本轮对比表占位（E3）判"部分兑现"；verify PASS；assemble+validate PASS。

示意输出（consistency 摘要）：

```json
{
  "overall_pass": true,
  "round": 2,
  "n_regions": 3, "n_exempt": 0,
  "op_region": {"E1": "D1", "E2": "D3", "E3": "D3", "E4": "D2", "E5": "D2"},
  "n_promises": 1
}
```

承诺台账条目（示意）：`PR1 | "我们将在下一轮补充对比表" | prev_response_round1.md | 部分兑现 | R1-C1-s1/E3`。

## 6. 资源清单

- `scripts/`：init_result / inspect_case / parse_manuscript / parse_comments / revision_engine / verify_revision / **consistency_engine（主攻）** / assemble_result / validate_output（全部 stdlib）
- `references/schemas.md`：dispositions / edit_plan / consistency.json 等全部 JSON 契约
- `references/consistency_rules.md`：三方对账模型、diff region 判定与噪音豁免、承诺句式词表、多轮文件命名约定
- `templates/revision_ledger.md`：承诺台账模板 + 回复信引用规范
- `checklists/final_checklist.md`：交付前一致性自查清单
- `evaluation/scoring_sheet.md`：评分点-机制对照自查表
- `examples/minimal_example.md`：最小调用示例（合成数据，标明为示例）
