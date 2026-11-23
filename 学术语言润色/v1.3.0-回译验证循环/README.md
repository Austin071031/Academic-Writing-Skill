# academic-polish-backtranslation（学术语言润色 Skill v1.3.0）

回译验证循环驱动的学术精修：每处关键句修改都经"回译→主张矩阵逐格比对"验证，
漂移即修复或回退留证。把"没改坏"从口号变成可逐句出示的证据（drift_report.md）。

## 结构

- `SKILL.md`：入口与六阶段流程。
- `scripts/segment_util.py`：预检+提取+分句+关键句标注（【K】）+ result.json 骨架。
- `scripts/claims_check.py`：主张矩阵机读复核（回译留痕、claims 与原文逐格一致）。
- `scripts/terminology.py`：术语表构建与全篇回扫。
- `scripts/assemble.py`：产物组装（含 drift_report.md）。
- `scripts/validate_output.py`：发布闸门。
- `references/backtranslation_protocol.md`：回译协议与典型漂移处置。
- `references/editing_rules.md`：编辑规则速查。
- `examples/minimal_example.md`：最小调用示例（标注为示例）。

## 与姊妹版本的方向差异

v1.1.0 靠确定性脚本审校（外控）；v1.2.0 靠纯提示方法论（内省）；
v1.3.0 靠往返翻译验证（验证循环）；v1.4.0 靠文体指纹（目标驱动）；
v1.5.0 靠编辑批注制（人机协作）。五者交付同一契约，机制互不重合。
