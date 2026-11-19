# CHANGELOG

## v1.0.1（2026-11-19）

- 首版：公式一致性与排版合规方向（改得对·公式）。
- math_audit.py：M1-M7 七类公式 finding 普查（$$、eqnarray、编号/引用、文字下标、
  单位、裸算子、\left/\right 配对），只诊断不擅改，全部带 file:line 与改法建议。
- 共享核心与编译验证闭环同 v1.0.0（tex_build/tex_logscan/tex_check 等）。
- 本地合成案例验证：5 个植入缺陷全部命中，修复后 findings=0 且编译收敛。
