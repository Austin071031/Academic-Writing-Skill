# 最小调用示例（合成示例，非正式测试案例）

输入：task.md（"按 IMRaD 写完整初稿，3000 字"）、数据 CSV、实验记录 md、参考文献 txt。

```bash
bash /skills/weekly-skill/scripts/run.sh pre
# → outline.md：results 有 M01/M03 支撑；discussion 命中弱；数据可得性声明 ⚠ 无材料支撑
# Agent 写稿：discussion 正常写（依据结果与文献），声明字段写【待确认：材料未提供数据存储信息】
bash /skills/weekly-skill/scripts/run.sh post
# → completeness_report.md：8 节齐全、无跳级、篇幅 2650 字（-12% 可接受）→ PASS
```
