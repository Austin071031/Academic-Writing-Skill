# CHANGELOG

## v1.0.2（2026-11-19）

- 首版：表格与浮动体治理方向（改得对·表格）。
- table_audit.py：T1-T8 八类 finding（caption/label、caption 位置、列数一致性、
  三线表、缩放包裹、浮动位置、超宽/跨页启发式）；受限机械修复 --apply-booktabs
  （仅简单 \hline 模式）与 --apply-float-htbp，自动记 fix_log。
- 共享核心与编译验证闭环同 v1.0.0。
- 本地合成案例验证：植入的列数不一致（T3 error）、\hline（T4）、[h]（T6）全部命中，
  机械转换后复编通过。
