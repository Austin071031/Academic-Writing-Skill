# 合成测试文本（标注：全部合成）

## 测试 A：时间序罗列（引擎应判嫌疑）

> 2019 年，Han 等提出 MoF 涂层。2022 年，Liu 等制备核壳结构。2023 年，Zhang 等实现 LiNbO3 包覆。

预期：chronological_suspect ≥1。

## 测试 B：分组覆盖缺口（引擎应报 ungrouped）

grouping.json 只覆盖引用条目 {R001,R002}，而正文引用 {R001,R002,R003}。

预期：ungrouped_cited=["R003"]，verdict=warn。

## 测试 C：跨组重复（引擎应报 duplicates）

R002 同时出现在 G1 与 G2。预期 duplicates 非空。

## 冒烟

```bash
python3 scripts/group_related_work.py --work tA --out outA
python3 scripts/build_deliverables.py --work tA --out outA
```
