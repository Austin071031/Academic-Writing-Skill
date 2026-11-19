---
name: results-discussion-structuring
description: 结果与讨论章节写作的"结果描述结构化"方向技能。当任务要求把已有科研发现写成结构清晰的结果段（按图序或按研究问题组织），并保证结果段只陈述观察、讨论段才承担解释时使用。核心能力：两种组织模式的段落骨架、描述/解释词汇边界、结构自检脚本（检测结果段混入解释、因果与评价词汇、段落无图锚点、流水账结构）。适用于换图、换学科、换数据量后继续产出可用章节。
---

# 结果与讨论章节写作：结果描述结构化方向

## 1. 用途与适用条件

本 Skill 解决科研写作中的结构失败点：**结果段写成流水账、描述与解释不分、主次颠倒、段落之间缺乏逻辑推进**。基础 Agent 常把"观察到的事实"和"对事实的解释"混写，或在结果段直接讨论机制，导致两节互相顶替。

适用条件：输入材料（论文 PDF/图表/数据）已存在，要求产出结果段与讨论段。若材料不足以致无法组织结果段，按第 4 节声明缺口。

核心原则：

1. **结果段 = 观察的目录**：只写"看到了什么"，每句可由图/表直接支撑。
2. **讨论段 = 解释的法庭**：解释、文献对照、机制推测、局限全部在此，且推测必须标注。
3. **结构先行**：先列发现清单（finding list）和段落大纲，确认结构后再写正文；不允许边想边写。
4. **自检闭环**：交付前运行结构自检脚本，未通过必须修改。

## 2. 输入与输出

输入：`/input/case.json`（case_id、output_contract）、`/input/task.md`（文体/语言/受众/篇幅）、`/input/` 下科研材料。按实际扩展名识别文件，不凭文件名假设内容。

输出（写入 `/app/output/`）：

| 文件 | 说明 |
|-|-|
| `result.json` | 含 case_id、output_contract 全部字段、status、sources、uncertainty、change_log |
| `results_and_discussion.md` | 可编辑章节：结果部分 + 讨论部分 |
| `outline.md` | 段落大纲与发现清单（体现结构决策，供复核） |
| `structure_report.json` | 结构自检脚本输出 |

有 pandoc / LaTeX 时另生成 docx / PDF 预览，否则在 result.json 注明。

## 3. 工作流程

### 步骤 1：读契约、定规范（1–2 次模型请求）

读取 case.json 与 task.md：记录 case_id、output_contract 字段、语言、篇幅上限、目标期刊/受众（决定详略与术语深度）。将 output_contract 字段写入 `/app/work/contract_fields.txt`。

### 步骤 2：抽取材料、列发现清单

用 `reference/tool_recipes.md` 的命令抽取材料全文与图表内容（pdftotext、渲染图页、读数据表）。然后写**发现清单** `/app/work/findings.md`：逐图/逐表列出观察条目，每条一句话、只写事实，格式：

```
F1 [图1A] 处理组 X 指标为 (61.4 ± 3.8)%，对照组 (95.2 ± 2.1)%，n=3，p=0.002。
F2 [图1B] X 指标变化与剂量正相关（10/20/50 µM 三组）。
...
```

发现清单是段落大纲的唯一素材来源；清单外的内容不得进入正文。

### 步骤 3：选择组织模式并写段落大纲

按 task.md 指定选择；未指定时默认**模式 A（按图序）**。决策规则见 `templates/organization_patterns.md`：材料含明确递进式研究问题（Q1→Q2→Q3）时用模式 B（按问题），每段可跨图引用。

写 `/app/output/outline.md`：每段给出（a）段旨一句话；（b）覆盖的发现编号；（c）引用的图表；（d）段落类型（呈现型/比较型/阴性结果型）。阴性结果与意外结果必须各占一条目，不得省略。

### 步骤 4：撰写结果段

严格按 `templates/paragraph_skeletons.md` 的段落骨架写作，遵守：

- 每段以主题句开头（该段观察回答什么问题），段内按"总体→分组→关键点"或时间/剂量梯度推进。
- 每句带图/表锚点（图2B、表3），写到子面板级。
- 只准使用描述性谓词（升高、降低、保持不变、呈剂量依赖……），禁止解释性谓词（因为、由于、说明、表明、提示……机制、可能是……所致）。
- 段落长度均衡：避免一段 300 字、一段 40 字；篇幅由 task.md 约束。

### 步骤 5：撰写讨论段

按 `templates/paragraph_skeletons.md` 的讨论五语步（复述→对照→解释→意义→边界）写作。机制推测一律写「我们推测……（推测，尚待验证）」；每条论断后跟锚点【数据：图x】或【文献：…】。引用只能来自材料提供的参考文献列表。

### 步骤 6：结构自检

```bash
python3 /skills/weekly-skill/scripts/check_structure.py \
  --text /app/output/results_and_discussion.md \
  --outline /app/output/outline.md \
  --out /app/output/structure_report.json
```

脚本检测（详见 `reference/structure_rules.md`）：

1. 结果部分是否混入解释性/因果性/评价性词汇（suggests that、表明、由于、令人惊讶地……）——按句定位报告；
2. 结果部分每个段落是否含至少一个图表锚点；
3. 段落长度离散度（最长/最短比 > 5 视为失衡）；
4. 讨论部分机制推测是否带标注；
5. outline 中的发现编号是否全部在正文出现（防漏写）。

未通过项必须修改正文后重跑，直至全部通过或在 result.json 的 uncertainty 中说明保留理由。

### 步骤 7：交付

生成 `result.json`（字段同 v1 规范：output_contract 全字段 + case_id + status + sources + uncertainty + change_log），生成 docx/PDF（环境允许时），按 `checklists/final_checklist.md` 逐项自查。

## 4. 异常处理

| 情况 | 处置 |
|-|-|
| 材料只有图无数值 | 发现清单写定性观察（趋势、有无、相对大小），标注 [定性]，正文不写精确数值 |
| 图表数量极少（1–2 张） | 模式 B 优先；一段一图拆细会导致碎片段落，合并为一到两段 |
| 结果与讨论边界由 task.md 另行规定（如合写一节） | 以 task.md 为准，但段内仍须用标记（如小标题"结果"与"讨论"）分隔观察与解释，并在 change_log 说明 |
| 发现清单中出现相互矛盾的观察 | 两条都保留，正文如实并陈，矛盾写入 uncertainty |
| 自检脚本与人工判断冲突 | 以脚本报告为准修改；确属误报时在 uncertainty 记录"structure_report 第 N 项为误报，原因……" |

## 5. 最小调用示例（示意，非真实案例答案）

输入（示意）：`/input/case.json` 含 `{"case_id":"demo-02","output_contract":["section_md","language"]}`；材料为一篇含图1（A/B 两面板）、图2（A–C 三面板）的论文 PDF。

调用：Agent 抽取材料→写 findings.md（F1–F6）→选模式 A→写 outline.md（结果 2 段 + 讨论 1 段）→写正文→跑 check_structure.py 通过→交付。

示意输出（节选）：

```json
{
  "case_id": "demo-02",
  "section_md": "## 结果\n如图1所示……（段1，图1A–B）……如图2所示……（段2，图2A–C）……\n## 讨论\n本研究观察到……【数据：图1B】……与 Zhang 等（2020）一致……我们推测……（推测，尚待验证）……",
  "language": "zh",
  "status": "success",
  "sources": {"outline": "outline.md", "structure_report": "structure_report.json"},
  "uncertainty": [],
  "change_log": ["初稿结果段第2段混入机制解释，已移至讨论段"]
}
```

## 6. 资源清单

- `scripts/check_structure.py`：结构自检脚本（stdlib）。
- `templates/organization_patterns.md`：两种组织模式的决策规则。
- `templates/paragraph_skeletons.md`：结果段与讨论段段落骨架。
- `reference/style_lexicon.md`：描述性/解释性/评价性谓词词表。
- `reference/tool_recipes.md`：材料抽取命令清单。
- `reference/structure_rules.md`：自检脚本判定规则说明。
- `checklists/final_checklist.md`：交付前自查清单。
