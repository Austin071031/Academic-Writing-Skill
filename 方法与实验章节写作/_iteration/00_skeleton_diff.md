# 表 3 · 版本骨架对照（v1.0.0–v1.0.4 实读目录，2026-11-23）

每版：根 21 文件 + submission/ 镜像 13 文件 = 34 文件（打包时 outputs/+results/ 双份 → bundle 内 ~68 文本文件）。

## 共有文件（基线资产白名单取数依据）

| 路径 | 作用 |
|-|-|
| SKILL.md | 技能入口（YAML frontmatter name/description + Phase 0–5 流程 + 异常处置表） |
| submission/SKILL.md + submission/scripts + submission/references | 评测环境 /app/submission 镜像（13 文件） |
| scripts/init_result.py | Phase 0：防超时空手，先落 result.json 骨架（case_id + output_contract 字段） |
| scripts/inspect_case.py | Phase 1：case.json/task.md 解析、材料分类、PDF 按页文本化（pdftotext，===== PAGE k =====） |
| scripts/extract_evidence.py | Phase 1：要素候选抽取（seed/hyperparam/size/split/dataset/hardware/version/command/url/env_var）→ evidence_candidates.jsonl + value_index.json |
| scripts/build_deliverables.py | Phase 4：七节装配 + 锚点解析 + 附录A参数表/B证据对照/C缺口清单 + result.json 组装 |
| scripts/validate_output.py | 发布闸门：契约字段、outputs 存在性、六要素覆盖、未解析锚点、占位符 |
| scripts/render_previews.py | 章节 PDF/TXT 预览（pandoc 缺失降级） |
| references/six_elements_checklist.md | 六要素逐项核对清单 |
| references/parameter_table_template.md | 参数表字段规范（name/value/unit/scope/source_eid） |
| references/gap_question_checklist.md | 缺口分级与追问句式 |
| README.md / docs/USAGE.md / CHANGELOG.md / GITHUB_URL.txt / examples/minimal_example.md / evaluation/scoring_sheet.md / evaluation/smoke_test.md / SUBMISSION.md | 文档与记录 |

## 各版独有文件（方向机制）

| 版本 | 独有脚本（引擎） | 独有规则 |
|-|-|-|
| v1.0.0 | scripts/audit_provenance.py（正向数值泄漏 + 反向台账闭合） | references/evidence_anchor_rules.md |
| v1.0.1 | scripts/element_matrix.py（18 格覆盖 + scope 违规 + 串台启发） | references/condition_matrix_rules.md |
| v1.0.2 | scripts/repro_gate.py（复现七要素闸门 + 命令入章校验） | references/reproduction_checklist_rules.md |
| v1.0.3 | scripts/cross_source_check.py（跨源多值机检 detect/verify 双阶段 + 裁决覆盖率） | references/consistency_rules.md |
| v1.0.4 | scripts/exp_matrix.py（实验矩阵 + 可比性闸门 + R# 引用闭环） | references/statistics_style_rules.md |

## §2.1–2.4 推导

- **N = 3**：平台公开得分（81.0/80.3333/79.6667/79.3333/79.0/78.6667 及写作10 的 67.3333/68.6667/60/73.6667）×3 全为整数 → 3 个评分单元（对应"平台固定运行 3 个案例"），单点机制增益兑现 = G÷3。
- **W**：本账号 5 版全部未出分（evaluation_error），**无法从自身数据推导分数带**。旁证（非裁决依据）：本题公开出分带 78.67–81.0，W≈2.33 ≪ 80×0.12，提示方向差异对最终分贡献小、提分空间在共性层。
- **白名单**：上表"共有文件"6 个脚本 + 3 个模板 + SKILL.md 流程。修复版必须资产守恒。
- **契约**（00_contract.md 要点）：输入 /input/case.json+task.md；输出 /app/output/result.json（含 output_contract 全字段+case_id）+ 可编辑产物；技能安装 /skills/weekly-skill；资源 ≤50 UTF-8 文本文件；预算 64 请求/900s/16384 token。
