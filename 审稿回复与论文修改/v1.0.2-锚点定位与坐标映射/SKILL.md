---
name: revision-anchor-localization
description: 审稿回复与论文修改的"修改定位"方向技能。当任务要求交付修订稿与逐条回复信、且回复中每一处定位（E# 操作、引文、段落/章节/行号坐标）必须能在指定版本稿件中被独立核对时使用。核心能力：把每处改动映射到稿件版本、章节、段落、行号与可检索原文锚点——基线侧坐标（章节+段 ID+基线行号）与修订侧坐标（修订行号+段 ID+新文本摘录）双坐标成对记录；用行级 diff 建立基线↔修订稿行号映射与变更区域；自动核验回复信中的 E# 引用、引号引文与坐标声明是否真实存在于修订稿，任何"声称改了但定位不到"的声明被引擎拦截；模糊锚点单独预警。使定位在改稿后仍然有效、可被第三方独立核对。适用于受控返修演练与真实返修的修改定位与可核验性保障阶段。
---

# 审稿回复与论文修改：锚点定位与坐标映射

## 1. 用途与适用条件

本 Skill 解决返修交付中最伤可信度的一类失败：**回复信里说"已在第 X 节第 Y 段修改"，审稿人却找不到**——行号沿用了改稿前的旧稿、引文与修订稿文字对不上、E# 操作编号悬空、新增段落没有坐标可引用。

核心原则：

1. **双坐标定位**：每处改动同时给出基线侧坐标（章节标题、para_id、基线行号）与修订侧坐标（修订稿行号、段 ID、新文本前 30 字摘录），两侧互相印证，改稿后仍可回溯。
2. **行号映射而非手抄**：基线↔修订稿的行号对应由 difflib 行级对齐自动算出（change regions），Agent 不手写行号，杜绝"旧稿行号残留"。
3. **回复信定位声明可独立核对**：回复信中每一个 E#、每一段引号引文、每一个 P###/SEC#/第 N 行坐标，都由 anchor_engine 对照修订稿逐项核验；核不到的声明列入 unresolvable_claims 并使引擎 exit 1，不允许带着空话交付。
4. **修改必须真实落稿**：声称的每处修改通过锚点编辑引擎真实应用到基线；模糊锚点单独预警"人工复核定位"，失效锚点如实标注"锚点已由改写消除"，不假装定位精确。

适用条件：输入含可读的基线稿件（md/txt/tex/docx/pdf）与审稿意见文件；已完成（或可在步骤 3 手工完成）意见拆解与处置决策。

## 2. 输入与输出

输入：`/input/case.json`（case_id、output_contract）、`/input/task.md`、`/input/` 材料（典型为 `materials/manuscript-baseline.md` 与 `materials/reviewer-comments.md`，名称可能不同，由侦察脚本判定）。

输出（写入 `/app/output/`）：

| 文件 | 内容 |
|-|-|
| `result.json` | output_contract 全字段 + case_id + status + sources + uncertainty + change_log |
| `revised_manuscript.md` | 可编辑修订稿（锚点编辑真实应用后的全文） |
| `response_letter.md` | 逐条回复信草案（子要求级，含决策与可核对定位声明） |
| `location_table.md` | **由 anchor_engine 自动生成**的修改定位表（op_id/意见/动作/基线坐标/修订稿坐标/锚点摘录/状态 + 变更区域 + 模糊锚预警 + 回信声明核验结果） |
| `evidence_checklist.md` | 未到位证据清单（补实验/数据/文献的需求、状态、替代说明） |
| `verification.json` | 五重交叉核验结果 |
| `anchor_map.json` | 引擎中间产物（留在 work/）：双坐标明细、行级映射、声明核验明细 |

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

读 `/app/work/inspection.json`：确认 `baseline_candidates[0]` 与 `comment_candidates[0]` 是否符合预期。判错时用 `--file` 显式指定。issues 记入 `/app/work/exceptions.json`（JSON 列表）。

### 步骤 2：解析基线结构

```bash
python3 $SKILL/scripts/parse_manuscript.py --work /app/work
```

产出 `structure.json`：章节（SEC#）/段落（P###）稳定 ID 与 `source_file` 基线路径——这是双坐标中基线侧坐标的锚定来源。读一遍段落清单，建立稿件内容地图。

### 步骤 3：解析并拆解意见

```bash
python3 $SKILL/scripts/parse_comments.py --work /app/work
```

**由你（Agent）复核 `comments.json`**：拆分漏了子要求 → 补行（保持 sub_id 如 R1-C1-s2 递增）；背景句被当成要求 → 合并；type/severity 初判错误 → 修正。本方向不追求拆解引擎，但 sub_id 是后续定位表的"意见"列与回复信编号的基准，必须准确。

### 步骤 4：制定处置决策与编辑计划

写 `/app/work/dispositions.json`（schema 见 `references/schemas.md`）：每个子要求一条，含 `decision`（采纳/部分采纳/不采纳）、`response`（≥20 字且含可核查指涉）、`edit_ops`、`evidence`、`tone`。

写 `/app/work/edit_plan.json`：每处修改一条操作，`anchor_quote` 必须是**从 structure.json 段落原文逐字复制的片段**（≥10 字、含特征词）。锚点质量直接决定双坐标中基线行号的可靠性，禁止凭记忆改写锚点。

### 步骤 5：应用编辑

```bash
python3 $SKILL/scripts/revision_engine.py --work /app/work --out /app/output
```

exit=2 表示有失败锚点：读 `work/edit_report.json` 的 reason，修正 quote 或加 `para_id` 后重跑。**不得无视失败继续。**

### 步骤 6：自动生成定位表（本 Skill 主攻步骤）

```bash
python3 $SKILL/scripts/anchor_engine.py --work /app/work --out /app/output
```

引擎一次完成三件事：

1. **双坐标定位**：edit_report 每个 applied op 生成基线侧坐标（章节+para_id+基线行号，逐行搜索 anchor_quote；找不到记"锚点已由改写消除"并用 method/ratio 说明）与修订侧坐标（revised_line+段 ID+new_text 前 30 字）；
2. **行级映射**：difflib.SequenceMatcher 对基线与修订稿全文行级对齐，输出 change regions（基线行区间→修订稿行区间，按 op 的 revised_line 反查关联 op_id）；
3. 生成 `/app/output/location_table.md` 与 `work/anchor_map.json`。

此时回复信通常尚未撰写，引擎检测到无 `response_letter.md` 会**跳过声明核验**——这是正常分支，不是错误。

然后按 `templates/response_letter.md` 写 `/app/output/response_letter.md`，**严格遵守 `references/anchor_rules.md` 引文规范**：引用修订稿新文本必须引号包裹且逐字；坐标（P###/SEC#/行号）必须真实存在。同时写 `evidence_checklist.md`、`work/evidence_map.json`、`change_log.json`、`uncertainty.json`、`manual_confirmations.json`、`stats.json`。

### 步骤 7：定位声明核验 + 交叉核验

```bash
python3 $SKILL/scripts/anchor_engine.py --work /app/work --out /app/output   # 重跑：现在核验回复信
python3 $SKILL/scripts/verify_revision.py --work /app/work --out /app/output
```

anchor_engine 重跑时解析 `response_letter.md`：

- (a) 所有 E# 引用必须在 edit_report applied 集合内；
- (b) 所有引号（「」〈〉“” “”）包裹的 ≥8 字引文必须能在修订稿中找到（空白归一化子串；若与意见原文一致视为意见摘录，予以放行）；
- (c) 所有 P\d{3}[a-z]? / SEC\d+ / 第?\d+行 坐标引用必须合法（段/章节 ID 存在、行号 ≤ 修订稿总行数）。

任何不可核对声明列入 `unresolvable_claims` 并 **exit 1**。**回复信手改后定位失效应重跑本引擎**（见异常表）。修复后重跑至 exit 0，再跑 verify_revision 五重核验；FAIL 项修复后重跑，无法修复的把 status 降级为 partial 并在 uncertainty 说明。

### 步骤 8：汇总交付

```bash
python3 $SKILL/scripts/assemble_result.py --work /app/work --out /app/output \
  --case /input/case.json --skill "revision-anchor-localization v1.0.2" --status success
python3 $SKILL/scripts/validate_output.py --out /app/output --work /app/work
```

validate PASS 后结束；FAIL 按提示修复或如实降级 status。

## 4. 异常处理

| 情况 | 处置 |
|-|-|
| 找不到意见文件或基线文件 | inspect issues 记录；status=failed 并说明缺什么，不编造内容 |
| 基线文件不可读（路径失效/编码损坏） | anchor_engine 降级为 structure 段落模式：基线行号标注为"结构伪行号"并 WARN；在 location_table.md 注明 baseline_mode，结果仍可用但须人工知悉 |
| 锚点不唯一（quote 多处出现） | revision_engine exit=2；加长 quote 或指定 para_id+section 后重跑；不得让引擎猜位置 |
| 模糊锚点（method 以 fuzzy 开头） | 不判失败，但 location_table.md 单列"⚠ 模糊锚点预警"，提示"锚点为模糊匹配，人工复核定位"；人工复核结论写入 manual_confirmations |
| 锚点已由改写消除（基线行号找不到） | 基线坐标标注"锚点已由改写消除"，附 method/ratio 与最佳相似度；该 op 的修订侧坐标不受影响；列入 uncertainty 说明 |
| 新增段落无基线坐标 | 双坐标规范：insert_* 的新增段（P005a）基线侧坐标落到其锚段（anchor_para）的行号，修订侧用新段 ID；回复信中引用新增段用新段 ID + 修订稿行号，禁止虚构基线行号 |
| 回复信中 E# 引用悬空 | anchor_engine exit=1（E引用悬空）；核对 edit_report，改用已 applied 的 op_id 或先补做对应编辑 |
| 回复信引文与修订稿对不上 | anchor_engine exit=1（引文未找到）；引文必须逐字抄自修订稿（空白归一化后子串匹配），改文字后必须同步改引文 |
| 回复信手改后定位失效 | 任何对 response_letter.md 的手改（加引文、改行号）后**必须重跑 anchor_engine**；不得凭印象认为"应该还能对上" |
| 行号越界（第 N 行超出修订稿总行数） | anchor_engine exit=1（行号越界）；行号以 location_table.md 为准，不许引用旧稿行号 |
| 要求补实验/数据/文献 | 修订稿插【待补：…】占位 + 证据清单"无法补做+替代说明"；不得编造数据 |
| PDF 材料抽取失败 | exceptions 记录；若另一材料可读则继续并 status=partial |
| 重复运行 | 脚本幂等；改 edit_plan 后须先重跑 revision_engine 再重跑 anchor_engine，否则定位基于旧修订稿 |

## 5. 最小调用示例（示意，非真实案例答案）

输入（示意）：case.json 含 `{"case_id":"demo","output_contract":["revised_manuscript","response_letter","edit_locations","evidence_checklist"]}`；材料为 8 段基线 + 2 位审稿人 5 条意见。

调用：步骤 0→8 顺序执行；parse_comments 得 5 意见 7 子要求；Agent 写 7 条 disposition、5 条 edit op；revision_engine 应用 5/5；anchor_engine 首跑生成 location_table.md（5 个 op 全部双坐标、3 个变更区域）；Agent 写信并引用修订稿原文；anchor_engine 复跑核验 6 处 E# + 1 处引文 + 3 处坐标全部可核对，exit=0；verify 五重 PASS。

示意输出（result.json 节选）：

```json
{
  "case_id": "demo",
  "status": "success",
  "outputs": {"revised_manuscript": "revised_manuscript.md", "response_letter": "response_letter.md",
              "location_table": "location_table.md", "verification": "verification.json"},
  "stats": {"n_comments": 5, "n_subs": 7, "n_ops_applied": 5},
  "verification_overall": true
}
```

## 6. 资源清单

- `scripts/`：init_result / inspect_case / parse_manuscript / parse_comments / revision_engine / **anchor_engine（主攻）** / verify_revision / assemble_result / validate_output（全部 stdlib）
- `references/schemas.md`：dispositions / edit_plan / evidence_map 等全部 JSON schema 与填写规则
- `references/anchor_rules.md`：双坐标规范、引文引用规范、行号映射方法、失效锚点定义与处置
- `templates/location_table.md`：location_table.md 各节段说明模板（正文由引擎生成）
- `templates/response_letter.md`：回复信模板（含定位声明写作规范）
- `checklists/final_checklist.md`：交付前自查清单
- `evaluation/scoring_sheet.md`：评分点-机制对照自查表
- `examples/minimal_example.md`：最小调用示例（合成数据，标明为示例）
