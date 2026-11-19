# 缺口与追问清单模板（work/gaps.json → 附录C / result.json）

```json
[{"element": "对照实验", "desc": "基线结果数值未在材料中出现",
  "severity": "high|medium|low", "question_for_author": "请提供基线在 test 集上的 Accuracy 数值或其结果文件路径",
  "status": "unresolved|confirmed_by_material|written_with_caveat"}]
```

## 必须追问（high）的典型情形

1. 参数无任何来源（配置/日志/代码/论文都没有）。
2. 数据集只有名称没有版本或获取方式。
3. 基线对照的预算/划分/评测协议不明，无法判断可比性。
4. 日志与配置对同一参数给出不同取值且无法判定哪个生效。
5. 材料文件损坏、加密或权限不足无法读取。

## 追问句式（附录C展示用）

- "材料未给出 X 的取值/版本/条件；当前稿件未写入该值，请确认。"
- "A 文件记 X=v1，B 文件记 X=v2；本稿暂按优先级采信 v1，请确认。"

## status 语义

- `unresolved`：已追问未获确认 → 计入 result.uncertainty，status 至多 partial。
- `confirmed_by_material`：写作过程中在材料里找到了答案 → 正文补写并挂锚点。
- `written_with_caveat`：作者材料允许带保留地写（如"单次运行结果"）→ 正文写明口径。
