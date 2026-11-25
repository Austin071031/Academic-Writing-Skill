# 评分细则自审规范（rubric audit）

交付 `rubric_audit.md`：把题面评分细则变成一张逐条核对表，每条给状态与证据位置。
这是给评审准备的"复核地图"，也是防止漏项的最后闸门。诚实是底线：未达项如实写。

## 自审表格式

```markdown
# 评分细则自审（rubric audit）

## 一、实际效果（40 分对应项）

| 检查点 | 状态 | 证据 |
|---|---|---|
| 交付润色后完整文本（非提纲/建议/整段重写） | 达成 | polished.md 全文，change_log 逐句对照 |
| 指定章节逐段处理，范围无遗漏 | 达成 | change_log.md 句 ID 覆盖第 1–3 节全部段落 |
| 限定强度无升降（可能/有望/约 等） | 达成 | conservation_check.md 第 4 行 |
| 数据与单位未被改动 | 达成 | conservation_check.md 第 1 行 |
| 引用编号与图表指向对得上 | 达成 | conservation_check.md 第 2–3 行 |
| 术语表建全且全篇统一 | 部分达成 | terminology_table.md；B7-S4 存疑待确认 |
| 缩写与符号首次出现统一 | 达成 | change_log.md abbreviation 类卡片 |
| 中英双语对照齐全（若任务要求） | 达成 | sentence_alignment.md |
| 每处修改有原文/改文/类型/理由 | 达成 | change_log.md，抽样 B3-S2 |

## 二、使用增益（25 分对应项）

| 检查点 | 状态 | 证据 |
|---|---|---|
| 语法修正稳定优于无约束改写 | 达成 | gain_evidence 或 change_log 计数 |
| 术语一致性有机制保障 | 达成 | terminology_table.md + 术语扫记录 |
| 语义保持有机制保障 | 达成 | conservation_check.md |
| 对照条件一致声明 | 达成 | result.json assumptions |

## 三、创新增益（15 分对应项）

| 检查点 | 状态 | 证据 |
|---|---|---|
| 术语表驱动全篇一致性 | 达成 | terminology_table.md |
| 限定强度守恒检查 | 达成 | conservation_check.md |
| 最小编辑原则 | 达成 | change_log.md keep 卡比例与理由 |
| 改后回读校验 | 达成 | 回读签署（conservation_check.md 末尾） |

## 四、可靠体验与生态（20 分对应项）

| 检查点 | 状态 | 证据 |
|---|---|---|
| 材料缺口/编码问题如实标注 | 达成 | result.json uncertainty |
| 需要人工确认的内容明确标注 | 达成 | result.json manual_review_required |
| 文档与示例齐全 | 达成 | SKILL.md / examples/ / references/ |
```

## 处理项覆盖清单（完整性硬闸门，逐项打勾）

- [ ] 指定章节逐段处理（任务限定的范围 100% 覆盖）
- [ ] 术语表建立并全篇执行
- [ ] 缩写与符号首次出现形式统一
- [ ] 中英双语对照（任务要求时）
- [ ] 逐句修改清单（含 keep 句）
- [ ] 守恒自查（数值/引用/图表/限定/否定/因果）
- [ ] result.json 含 case_id 与 output_contract 全部键
- [ ] 材料缺口、存疑句、假设均已标注

## 使用规则

1. 自审在**交付前**做，发现"未达"优先补救；补不了的如实保留并写明原因。
2. 每条证据必须指向真实存在的文件与可定位位置，不许写"略"。
3. rubric_audit.md 写入 /app/output 并列入 result.json artifacts。
