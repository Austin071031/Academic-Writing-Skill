# academic-polish-editcards（学术语言润色 Skill v1.5.0）

编辑批注工作流：诊断→处方双段制 + 置信度分级。先诊断后开刀，拿不准的一律不擅自改；
每条编辑一张卡（诊断/处方/理由/置信度），交付批注式手稿（`[E#]` 锚点逐条可裁决）、
采纳版全文、编辑卡与作者验收清单。把"讲得清"升级为"可逐条接受/拒绝"的协作协议。

## 结构

- `SKILL.md`：入口与六阶段流程。
- `scripts/segment_util.py`：预检+提取+分句+result.json 骨架。
- `scripts/annotate.py`：批注式手稿、编辑卡、验收清单、采纳版全文、result.json 组装。
- `scripts/terminology.py`：术语表构建与全篇回扫。
- `scripts/validate_output.py`：终检（契约闭环、覆盖率、confirm 卡进人工确认清单）。
- `references/edit_card_spec.md`：编辑卡字段与分级生效规则。
- `references/author_workflow.md`：作者裁决流程与反馈回流。
- `examples/minimal_example.md`：最小调用示例（标注为示例）。

## 与姊妹版本的方向差异

v1.1.0 双通道脚本审校；v1.2.0 零脚本纯提示；v1.3.0 回译验证循环；
v1.4.0 文体指纹；**v1.5.0 人机协作协议**（编辑批注制，裁决权交给作者）。
