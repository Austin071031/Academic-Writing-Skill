# 本地冒烟记录（合成材料）

材料同前。登记 repro_checklist 后：

1. repro_gate.py：七项齐全、命令入章 → verdict=pass。
2. 删除 seeds 后：missing=["seeds"] → fail，status 须降级 partial——闸门有效。
3. 把清单命令改为不在第六节出现：commands_not_in_chapter 命中——"命令必入章"有效。
4. build/validate PASS；result.json 含 repro 报告指针与契约字段。
