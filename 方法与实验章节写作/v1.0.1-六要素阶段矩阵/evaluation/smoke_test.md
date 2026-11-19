# 本地冒烟记录（合成材料）

材料同 v1.0.0。登记 18 格（val/test 多为 na+理由）后运行管线：

1. element_matrix.py：缺 0 格；scope="通用" 通过；verdict=pass。
2. 故意把"学习率 3e-4"写入 05_baselines.md 评测句 → crossing_flags 命中（verdict=fail），
   移回训练描述后 pass——串台检测有效。
3. build/validate 与 v1.0.0 一致 PASS；result.json 含 matrix 报告指针与契约字段。
