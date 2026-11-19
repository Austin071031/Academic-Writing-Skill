# 一致性检查清单（改得动 + 可核验）

## 机读检查（check_consistency.py 自动执行）
| 检查 | FAIL 条件 | 处置 |
|-|-|-|
| numbers | 正文实质数字在材料语料中找不到原串 | 必须返修：找到出处或删除/标待确认 |
| citations | 悬空引用（文献表无此编号/条目）；文献表条目未被引用 | 必须返修：补条目或删引用/删冗余条目 |
| sections | brief.required_sections 中章节缺失 | 必须返修：补章节或显式说明该节为何缺失 |
| placeholders | 存在【待确认】等占位 | WARN：逐条列入 result.json uncertainty |
| ref_fields | 文献条目缺年份/DOI | WARN：保持缺失不补假，列入 uncertainty |

豁免规则（避免误报）：年份一律豁免；图/表/节编号豁免；文献表段落内的卷期页年豁免；
【待确认】上下文中的数字豁免。数字匹配做千分位与尾随零归一化。

## 成稿前 Agent 自查（机读之外的语义项，逐条过）
1. **摘要—结果一致**：摘要中的每个数字在结果节出现且一致。
2. **正文—图注一致**：正文"如图 N"编号与图注编号一一对应；图注中的组别/样本量与材料一致。
3. **方法—结果闭环**：方法节宣布的每组实验/每个指标，结果节都有对应结果（或标缺口）。
4. **引用—论断对齐**：evidence_map 中 type=citation 逐条复核：条目主题与论断一致（不只作者年份对）。
5. **术语与缩写统一**：同一概念全文同一术语；缩写首次出现有全称；中英术语对照一致。
6. **单位与有效数字**：同一物理量单位统一（如任务要求统一，统一过程记入 change_log）。
7. **待确认闭环**：每个【待确认】都能在 result.json uncertainty 中找到对应行；每个 evidence_map type=gap 都有正文标注。
8. **可编辑性**：manuscript.md 标题层级连续（不跳级）、表格为 Markdown 表格、引用格式统一；
   docx 由脚本生成，内容与 md 一致（render_preview 逐步降级时已留痕）。

## 人工复核点（交付时向用户明示，写进 result.json uncertainty）
- 图片材料中的数值（脚本不读图，需人工核对原图）。
- bibliography.json 中 fields_complete=false 的条目（缺 DOI/年份，可能解析不全）。
- 材料口径冲突处的取舍（change_log 中有记录）。
- PDF 提取失败的材料（material_index 中 status=unreadable）。
