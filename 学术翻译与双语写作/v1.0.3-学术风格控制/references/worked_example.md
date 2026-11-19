# 完整标注示例（合成稿件，非正式案例结果）

> 全部内容为合成示意，非平台正式案例。

## 输入与初译（含直译腔，合成）

源文：> We prepared the precursor solution. The film was characterized by XRD.

初译（translations.jsonl）：

```jsonl
{"seg_id":"P005-s1","translation":"我们对前驱体溶液进行了制备。"}
{"seg_id":"P005-s2","translation":"薄膜被 XRD 进行了表征，取得了革命性的结果。"}
```

## style_engine audit 检出

| id | 类型 | 句段 | 改写指令 |
|-|-|-|-|
| STY-001 | 直译-动词名词化 | P005-s1 | “进行了制备”→“制备了” |
| STY-002 | 直译-被动滥用+动词名词化 | P005-s2 | “被 XRD 进行了表征”→“用 XRD 表征了” |
| STY-003 | 语域-宣传口吻 | P005-s2 | 删“取得了革命性的结果”（源文无此表述，兼犯红线 2） |

## Agent 修订

```jsonl
{"seg_id":"P005-s1","translation":"我们制备了前驱体溶液。"}
{"seg_id":"P005-s2","translation":"用 XRD 表征了薄膜。"}
```

复检：issues=0；change_log 自动记录两条 revise_translation（before/after）。

## 示意输出（示例，非正式案例结果）

- style_report.json：`{"metrics":{"de_per_100_chars":1.8,"passive_per_100_chars":0.0},"segments":[]}`（修订后）。
- report.md：含 metrics 改善幅度与两条已修订记录。
