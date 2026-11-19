# 本地冒烟记录（合成材料）

材料同前（本文 acc=0.913 有日志支撑；基线无数值）：

1. exp_matrix.py：R1/R2 同口径登记 → issues 为空 verdict=pass。
2. 把 R2 budget 改为 "20 epochs" → budget_mismatch fail，加 budget_waiver 后 pass。
3. 删除第五节中的 "R1" 字样 → row_not_cited fail——正文引用闭环有效。
4. build/validate PASS；基线缺口进 gaps(high) 与 manual_confirmations，status 按规则降级。
