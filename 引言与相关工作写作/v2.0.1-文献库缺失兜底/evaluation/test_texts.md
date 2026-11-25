# 合成测试文本（标注：全部合成，仅用于本地冒烟）

## 测试 A：含空转铺垫的坏背景段（引擎应命中）

> 近年来，钙钛矿太阳能电池受到广泛关注，具有重要理论意义。随着光伏技术的迅猛发展，
> 该领域已成为研究热点，其重要性不言而喻。

预期：anti_fluff 命中 ≥3 句（近年来/随着/热点/重要意义），verdict=warn 或 fail。

## 测试 B：锚定良好的背景段（引擎应通过）

> 未封装的钙钛矿器件在 85% 相对湿度下 500 小时后效率衰减约 35%〔E1〕；
> 现有封装材料的水汽透过率仍高于 10^-3 g/(m^2·day)〔E2〕。
> 如何在湿热工况下将衰减抑制到 10% 以内，仍是未解决问题。

预期：锚定比 ≥50%，问题信号 ≥1，verdict=pass。

## 测试 C：数字漂移检测（引擎/人工应捕获）

evidence quote="衰减约 35%"，正文写"衰减超过 40%"——判定转述不一致，须改正或标注。

## 冒烟流程

```bash
python3 scripts/anti_fluff.py --work tA --out outA --patterns references/anti_fluff_patterns.txt
python3 scripts/build_deliverables.py --work tA --out outA
```

tA/tB 目录需按 SKILL.md Phase 1 预置 inspection/manuscript/library/notes 解析产物。
