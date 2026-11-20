# 表 3 版本骨架对照（skeleton diff）

来源：源 B 仓库目录实读（`find 文献证据驱动写作/v1.0.* -type f`，2026-11-20）。五版目录结构完全一致（每版 16 个文件，含 SUBMISSION.md）。

## 共有文件（五版全部存在）= 基线资产白名单取数依据

| 文件 | 作用（实读脚本/文档确认） |
|-|-|
| `SKILL.md` | Agent 入口：frontmatter（name/description）+ 阶段 0–5 流程 + 异常决策表 + 自查清单 |
| `README.md` | 使用说明 + 评分维度自评映射 + 限制 |
| `CHANGELOG.md` | 版本变更 |
| `SUBMISSION.md` | attempt ID / 状态 / 得分回填 |
| `direction.json` | 方向标识与终检参数（被 validate_output.py 读取） |
| `docs/USAGE.md` | 调用步骤、输入输出解释、失败处理 |
| `examples/minimal_example.md` | 合成最小示例（明示非正式案例结果） |
| `references/method.md` | 方向方法详述（各版内容不同） |
| `references/rubric.md` | 判定口径速查表（各版内容不同） |
| `references/output_spec.md` | 输出文件格式规范（claims.jsonl/evidence.csv/draft.md/result.json 字段） |
| `references/edge_cases.md` | 异常情形处置（共用 + 方向专属） |
| `scripts/inspect_case.py` | 阶段0：解析 case.json/task.md → brief.json（case_id、契约键、材料盘点、issues） |
| `scripts/extract_text.py` | 阶段0：材料文本化（pdftotext→PyMuPDF→pypdf 降级链）→ /app/work/text/*.txt 带 `===== [PAGE n] =====` 页标记 → text_manifest.json |
| `scripts/init_result.py` | 阶段0：生成 result.json 骨架（递归复制 output_contract 键结构、case_id、status=partial） |
| `scripts/validate_output.py` | 终检 R1–R7：契约字段递归覆盖、三段产物齐备、claims/evidence 结构合法、**R5 摘录逐字命中（含页码反查）**、R6 成稿覆盖论断、方向专属检查（读 direction.json）→ validation_report.json + 回写 result.json status |
| `scripts/run_pipeline.sh` | 阶段0 一键预检（串调上述三脚本） |

## 各版差异（仅内容差异，无结构差异）

| 版本 | SKILL.md 阶段2/3 专属步骤 | direction.json 参数 | references 专属内容 |
|-|-|-|-|
| v1.0.0 | 文档画像（doc_profile.json）+ 逐字摘录 SOP + coverage_report | direction=evidence-extraction | doc_type 判定特征、摘录六条铁律 |
| v1.0.1（基线） | 原子论断切分 + 五值支撑匹配 + claim_source_matrix.csv | direction=claim-source-linking | 切分规则、五值支撑表、status 推导 |
| v1.0.2 | 引用清点登记 + 三方核验（citation_audit.csv、reference_registry.json） | direction=citation-accuracy | 三方核验清单、verification_path 格式 |
| v1.0.3 | 四维分级 + strength_rationale.csv + 措辞校准 | direction=evidence-strength + strong_verbs 词表 | A–D 分级表、分级—措辞对照 |
| v1.0.4 | 确定性五级定级 + 触发点改写 + hedging_report.json | direction=uncertainty-expression + causal/absolute_markers 词表 | 五级口径、限定语词表、四类触发点 |

## 跨题资产盘点（L4 候选，本题基线未用）

来源：源 B 同仓库其他题目目录实读。

| 资产 | 所在版本 | 机制 | 本题基线（v1.0.1）是否已用 |
|-|-|-|-|
| 逐句修改留痕 + 限定强度守恒检查 | 学术语言润色/v1.0.0（guard_check.py、editing_playbook.md） | 每处修改记 原文/改文/受控类型/理由；数值/引用/图表指向/否定/因果词在改写前后守恒 | **未用**（基线 change_log 为自由文本，无 schema、无守恒机检） |
| 材料索引锚点 + 事实底稿 + 机读一致性核验 | 学术论文写作/v1.0.0 | 数值/单位/样本量全部带锚点溯源，成稿前一致性检查 | 部分（基线有证据表，但无成稿数值→证据的逐数值机检） |
| 渲染预览（PDF/PNG） | 学术论文写作/v1.0.0、学术格式与模板适配/v1.0.1（render_previews） | 可编辑产物配真实渲染预览供评审查看 | **未用**（基线仅交 markdown） |
