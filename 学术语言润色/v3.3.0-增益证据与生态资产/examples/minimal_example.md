# 最小调用示例（示意输出标注为示例，非正式案例结果）

## 输入

`/input/case.json`：`{"case_id":"demo-001","output_contract":{"polished_text":"润色后全文","change_log":"逐句修改说明"}}`
`/input/task.md`：按期刊论文语域润色 manuscript.md，保持数值与引用不变，交付改后全文与逐句修改说明。
`/input/manuscript.md`：

```markdown
## 摘要
我们做了一个新的算法，结果非常的好，准确率提高了3.2个百分点[1]。结果证明该算法是最好的。
```

## 调用方式

加载本 Skill 后，Agent 直接按 SKILL.md 执行：读输入 → 任务画像 → 逐句七问 →
全篇三遍回扫 → 写入 /app/output。无任何脚本需要运行。

## 示意输出（示例）

`/app/output/polished.md`：

```markdown
## 摘要
本文提出一种新算法，实验结果良好，准确率提高了3.2个百分点[1]。结果表明该算法具有优势。
```

`/app/output/change_log.md`（节选）：

```markdown
### 句 B2-S1
- 原文：我们做了一个新的算法，结果非常的好，准确率提高了3.2个百分点[1]。
- 改文：本文提出一种新算法，实验结果良好，准确率提高了3.2个百分点[1]。
- 决策：modify ｜ 类型：register, collocation
- 理由：“做了/非常的好”口语化；去人称主语；数值与引用编号逐字保留。

### 句 B2-S2
- 原文：结果证明该算法是最好的。
- 改文：结果表明该算法具有优势。
- 决策：modify ｜ 类型：hedging, register
- 理由：“证明…是最好的”强断言+最高级，单数据集证据不足，降至中档并去最高级；已列人工确认。
```

`/app/output/conservation_check.md`（节选）：数值与单位：一致；引用：一致；限定强度：S2 有降档
处置（见 change_log 与 result.json manual_review_required）；其余：一致。
