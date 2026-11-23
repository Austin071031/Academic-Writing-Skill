# 编辑卡规范（edit card spec）

## 卡结构（edit_records/*.jsonl 每句一行）

| 字段 | 说明 |
|-|-|
| id | 句 ID（与 source_dump.md 一致） |
| original | 原文（照抄） |
| action | apply（生效）/ confirm（待作者裁决，不生效）/ keep（保留） |
| diagnosis | 诊断：问题是什么、证据在哪、属哪类（无问题写"未见问题"） |
| prescription | 处方：apply 时为改后句；confirm 时为建议改法（不生效）；keep 时为原文 |
| reason | 理由：指向具体语言现象，≥8 字 |
| types | 受控词表（grammar/syntax/collocation/punctuation/spelling/long-sentence/terminology/abbreviation/register/redundancy/logic/clarity/hedging/formatting/other） |
| confidence | high（客观硬错误）/ medium（惯例性改法）/ low（判断性取舍） |
| note | 备注（可选） |

## 分级规则（处方生效门槛）

- high + 不涉禁动清单 → apply。
- 涉及限定强度升降、术语取舍、语义重述、证据强度判断、题面未明确的取舍 →
  low + confirm，**处方照写但不生效**，开人工确认卡。
- 诊断未发现问题的句子 → keep，写保留依据（"无语病""限定强度恰当"）。

## 批注标记约定（annotated_manuscript.md）

- `[E3]~~原文~~ → **改文**[/E3]`：已采纳修改，作者可对照编辑卡 E3 裁决。
- `[E5]原文[/E5]〔待确认：诊断摘要〕`：编辑未擅自改，建议见编辑卡 E5。

## 诊断词表（diagnosis 常用句式）

主谓不一致（X 为复数主语）、时态错位（方法应为过去时）、悬垂修饰（As shown 主句
主语不符）、口语词（X 属口语）、宣传词（X 无证据支撑）、术语漂移（X 与术语表 Y
不一致）、缩写首现无全称、冗余（X 删除不影响逻辑）、连接词滥用、指代不明、
长句失控（三层嵌套）、限定强度风险（改法将改变档位，转 confirm）。
