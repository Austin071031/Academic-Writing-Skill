# 输出文件规范（各版本共用）

所有产物写入 `/app/output/`；中间产物写入 `/app/work/`。所有表格字段名与下表逐字一致，便于脚本终检与第三方复核。

## claims.jsonl（论断清单，每行一条 JSON）

| 字段 | 类型 | 说明 |
|-|-|-|
| claim_id | string | 唯一编号，成稿中以 [claim_id] 标注，如 C01 |
| claim_text | string | 原子论断，一条一判，不嵌套多个判断 |
| status | string | supported / partial / conflicting / unsupported / out_of_scope |
| evidence_ids | array | 支撑证据编号列表，可为空（unsupported 时必须为空） |
| strength | string | A/B/C/D（v1.0.0 与 v1.0.1 可为空，由强度版本填写） |
| certainty | string | 确定/很可能/可能/有限提示/未知（不确定性版本必填） |
| notes | string | 边界、适用人群、冲突说明 |

## evidence.csv（证据表，UTF-8 带表头）

| 列 | 说明 |
|-|-|
| evidence_id | E01、E02… |
| doc_id | 对应 text_manifest.json 中的文档编号（D01_xxx） |
| location | 定位：页码（p.3）或章节（§2.1）或 页码+段落 |
| quote | 原文逐字摘录（≤300 字，完整句，禁止跨句拼接与改写） |
| doc_type | primary_study / review / guideline / consensus / preprint / editorial / dataset / other |
| support_type | direct / partial / background / conflicting / not_supporting / metadata |
| strength | A/B/C/D（按 references/rubric.md 口径） |
| claim_ids | 支撑的论断编号，分号分隔（多对多在此处与 claims.jsonl 双向一致） |

## draft.md（成稿）

- 满足 case.json 指定体裁、受众与格式；每个实质性论断句末标注 [C01] 式来源编号。
- 不支持或撤回的论断不进入成稿，须列入 claims.jsonl 的 out_of_scope 并说明。
- 文内引用编号与参考文献表（如有）逐一对应。

## result.json（结构化结果）

必须包含：`case_id`（与 case.json 一致）、output_contract 声明的全部字段（键名不改、结构不变、叶子不为 null）、
`status`（success/partial/failed）、`artifacts`（产物路径清单）、`assumptions`、`uncertainty`（不确定性清单）、
`change_log`（修改记录）、`exceptions`（异常）。由 init_result.py 建骨架、validate_output.py 回写校验摘要。
