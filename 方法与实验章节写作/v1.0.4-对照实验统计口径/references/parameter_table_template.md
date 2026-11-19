# 参数表模板（work/table_rows.json → 附录A）

每行一个参数：

```json
{"name": "learning_rate", "value": "3e-4", "unit": "—", "scope": "train", "source_eid": "E0005"}
```

字段规则：

- `name`：材料中的参数名（保留英文原名，正文可给中文释义）。
- `value`：与材料逐字一致的取值；单位并入 `unit` 时 value 只放数字。
- `unit`：单位或"—"；百分比、轮数、无单位均写"—"并在 value 体现。
- `scope`：作用对象与阶段，必须可辨认为 train/val/test/环境/通用之一，禁止"训练/评测通用"式含混。
- `source_eid`：支撑该取值的证据锚点；多源一致时填主来源，其余进 unused_evidence.json。

正文第三节的每个数值都要能在本表找到同行同值；build 后由 validate_output.py 做存在性检查，
数值一致性由 audit_provenance.py 的正向泄漏检查兜底。
