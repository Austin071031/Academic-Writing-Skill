# academic-polish-registerfit（学术语言润色 Skill v1.4.0）

文体指纹驱动的学术润色：用可计算指标（句长分布、限定词密度与档位、被动语态、
连接词密度、人称、口语词、宣传词）刻画语域，润色前后用同一把尺量两遍，
达标报告（style_report.md）随稿交付。"像不像目标文体"从主观判断变成可核验指标。

## 结构

- `SKILL.md`：入口与六阶段流程。
- `scripts/segment_util.py`：预检+提取+分句+result.json 骨架。
- `scripts/style_metrics.py`：profile（目标画像）/ compare（前后对比报告）。
- `scripts/terminology.py`：术语表构建与全篇回扫。
- `scripts/assemble.py`：产物组装；`scripts/validate_output.py`：发布闸门。
- `references/register_profiles.md`：五种文体画像区间与解读提示。
- `references/editing_rules.md`：先守恒后风格、换装手法表、reason 标准。
- `examples/minimal_example.md`：最小调用示例（标注为示例）。

## 与姊妹版本的方向差异

v1.1.0 双通道脚本审校；v1.2.0 零脚本纯提示；v1.3.0 回译验证循环；
**v1.4.0 目标文体指纹**（语域指标驱动，"说得像"可度量）；v1.5.0 编辑批注工作流。
