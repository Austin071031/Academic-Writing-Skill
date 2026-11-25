# academic-polish-surgical-rubric（学术语言润色 Skill v3.4.0）

父辈：v1.2.0 零脚本手术式（得分 69.67）。本版唯一新增：评分细则自审闭环——
交付前把题面四维评分点变成逐条核对表（状态+证据位置），处理项覆盖清单八项
硬闸门拦截漏项，随稿交付 rubric_audit.md 复核地图。

零脚本手术式方法论：把完整编辑规程（四步流程、逐句七问、受控词表、禁动清单、
修改卡格式、守恒自查表）压进提示，不依赖任何脚本与环境，把模型预算全部留给
编辑决策本身。与 v1.1.0（确定性脚本双通道）是同一任务的两个极端方向。

## 结构

- `SKILL.md`：唯一入口，自包含全部规程与产物格式。
- `references/lexicon.md`：限定强度三档词表、因果/相关、否定与量词、禁动清单。
- `references/register.md`：五种文体语域规则 + 语域扫清单。
- `references/chinglish.md`：中式英语 12 类病灶与修法。
- `examples/minimal_example.md`：最小输入→调用→示意输出（标注为示例）。

## 适用

任意长度、任意学科的学术文本润色；无 Python/依赖/路径约束；环境只有文件读写即可。
不适用：纯问答、整篇翻译。

## 产物（/app/output）

polished.md、change_log.md（逐句修改卡）、terminology_table.md、sentence_alignment.md
（要求双语时）、conservation_check.md（六行守恒自查表）、result.json（含 case_id 与
output_contract 全字段、assumptions、uncertainty、manual_review_required）。
