# 评测契约（§2.4，判死依据）

来源：源 A Runtime contract 原文 + 基线 v1.0.1 的 `references/output_spec.md` 与 `scripts/inspect_case.py`、`scripts/init_result.py` 实读。§0-8 = 否：**契约层键名/结构一个不改**。

| 项 | 内容 | 出处 |
|-|-|-|
| Skill 安装路径 | `/skills/weekly-skill`（SKILL.md + 文本资源） | 源 A "installs the actual Skill under /skills/weekly-skill" |
| 输入 | `/input/case.json`（含 case_id、output_contract）+ `/input/task.md` + 材料文件（PDF 等） | 源 A "original input is /input/case.json and task.md" |
| 工作区 | `/app/work` 中间产物；`/app/output` 最终产物 | 源 A "Work under /app/work; final actual results … under /app/output" |
| 必需产物 | `result.json`（含 output_contract 全部原始字段 + case_id）；本 Skill 另交 claims.jsonl / evidence.csv / draft.md（三段交付） | 源 A "result.json with all original output_contract fields and case_id"；评分表"三段交付" |
| result.json 纪律 | 键名不改、结构不变、叶子非 null；status 诚实（success/partial/failed）；含 assumptions/uncertainty/change_log/exceptions | 基线 output_spec.md + init_result.py 实现 |
| 预算 | 64 次模型请求 / 900 秒 / 单次响应 ≤16384 token（含推理） | 源 A "Execution budget: 64 model requests, 900 seconds, 16384 tokens" |
| 依赖 | 仅 Python 3.8+ 标准库；PDF 提取 pdftotext→PyMuPDF→pypdf 降级链；无网络 | 基线 SKILL.md 依赖段（§4-1 继承） |
| 资源限制 | ≤50 个 UTF-8 文本文件、单个 ≤500KB、总量 ≤2MB、无符号链接 | 源 A "at most 50 UTF-8 text files, 500KB each and 2MB total" |
| 异常降级 | 材料 failed→exceptions 且 status 降档；unsupported→open_questions；预算将尽→定格 partial | 基线 SKILL.md 异常决策表 |
| 禁做 | 不提交预制答案；不编造数据/软件状态 | 源 A "Do not submit prepared answers"；"Do not fabricate" |
