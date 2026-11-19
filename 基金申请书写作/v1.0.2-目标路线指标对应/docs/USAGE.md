# 使用说明（grant-alignment-matrix v1.0.2）

## 输入

| 路径 | 说明 |
|-|-|
| `/input/case.json` | 案例元数据（case_id、output_contract 等） |
| `/input/task.md` | 写作任务要求 |
| `/input/organizer-workorder.json` | 组织方补充约束（可选；存在时优先级最高） |
| `/input/*.{md,txt,tex,docx,pdf}` | 科研材料：原论文、前期成果、指南等（格式不限） |

## 输出（/app/output）

`proposal_draft.md`（清洁章节稿）、`proposal_annotated.md`（留痕版）、
`element_mapping.md`（七要素对照说明）、`alignment_table.md`（四节对应矩阵表）、
`report.md`、`preview.html`、`result.json`。
中间产物（/app/work）：`inspection.json`、`materials.json`、`materials_digest.md`、
`fact_ledger.json`、`fact_ledger.md`、`alignment_seed.json`、`alignment_matrix.json`、
`draft.json`、`source_audit.json`、`element_map.json`、`findings.json` 等。

## 调用步骤

严格按 `SKILL.md` 标准工作流 13 步执行。Agent 的三处核心判断：

1. **第 6 步 条目设计**：读 `materials_digest.md` + `inspection.json`，确定研究目标条数 n
   （2-4 条），研究内容/技术路线/考核指标按同一 n 设计；四节统一行首编号体例。
2. **第 7 步 分节写作**：`work/sections/NN_要素名.md`，强制证据标记〔F0001〕〔拟〕〔确认〕；
   内容条目呼应目标、路线条目写明"针对研究内容（X）"、指标条目写明"对应目标X"。
3. **第 12 步 复核修订**：处置 source_audit / element_findings / findings 三个文件中的
   每条发现（孤儿条目误报须驳回并写理由），修订后重跑第 8-11 步至 high 级清零。

引擎两步定位：

- **第 5 步 `alignment_engine.py seed`**：写作前首次运行打印条目设计指引；
  draft_builder 之后重跑打印四节条目计数（目标/内容/路线/指标），供自查条目数设计。
- **第 11 步 `alignment_engine.py audit --out $O`**：建相似度矩阵与编号互引图谱，
  机检 orphan_goal / orphan_content / orphan_metric（medium）、count_mismatch（high）、
  missing_section（high），并生成 `alignment_table.md`。

## 证据标记语法

| 标记 | 含义 | 机检行为 |
|-|-|-|
| `〔F0001〕` | 该句事实来自台账条目 F0001 | FID 必须存在；数字/引用与台账值比对 |
| `〔拟〕` | 拟开展/预期内容（考核指标必须标） | 段内数字不做材料外审计；体貌须为拟态 |
| `〔确认〕` | 材料不足/冲突，需人工确认 | 登记 manual_confirmations 后放行 |

## 条目编号体例（引擎可机检的行首模式）

`1.` `1、` `1)` `（1）` `（一）` `①` `目标一` `内容一` `步骤一` `指标一` `第一条`。
编号必须置于**行首**；连写在同一行的编号只切出一条并记 note。无编号节按段落整体
切条并记 note（可在 count_mismatch 中误伤计数，建议始终编号）。

## 对应判据速览

- 跨节两条目 trigram Jaccard ≥ 0.12（剥除〔…〕标记后计算）→ 对应；
- 条目正文显式引用他节编号（"针对研究内容（一）""对应目标一"）→ 直接判对应；
- 覆盖规则：每目标≥1 内容、每内容≥1 路线、每指标≥1 目标，违反 → orphan_*（medium）；
- 目标数≠内容数 或 内容数≠路线数 → count_mismatch（high，写明实际条数）；
- 四节任缺 → missing_section（high）。

## 自查方法

- `validate_output.py` 必须 PASS。
- `report.md` 的 findings 分级统计中 high 必须为 0（或全部"已驳回"并附理由）。
- `alignment_table.md` 对应总表中每个研究目标行的"对应研究内容/技术路线/考核指标"
  三列均不为 "—"。
- 抽查 `proposal_annotated.md` 中 3 处〔F〕标记，对照 `fact_ledger.md` 验证来源属实。

## 失败处理

任一脚本失败：读 stderr → 修复后重跑（全部幂等）→ 无法修复则保留已有产物，
`assemble_result.py --status partial` 交付并在 report.md 写明限制。
