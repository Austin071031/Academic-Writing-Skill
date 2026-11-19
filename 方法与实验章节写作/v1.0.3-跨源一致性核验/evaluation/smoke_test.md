# 本地冒烟记录（合成材料）

材料同前（三处 learning_rate 故意不一致）：

1. detect：conflicts.jsonl 记 1 条候选；3e-4 与 0.0003 归一同组，1e-3 为实质分歧值。
2. verify：无裁决时 unresolved=1 fail；补写裁决后 resolved=1 pass——闭环有效。
3. build/validate PASS；result.json change_log 含取舍记录，manual_confirmations 含基线缺口。
