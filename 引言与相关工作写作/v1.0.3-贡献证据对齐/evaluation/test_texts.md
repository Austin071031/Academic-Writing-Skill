# 合成测试文本（标注：全部合成）

## 测试 A：数字不可回溯（引擎应报）

statement="容量保持率达 95%"，证据位置 P009 文本只有 91.3% → 数字不可回溯。

## 测试 B：幻影证据位置（引擎应报）

evidence_locs=["P999"] → "P999 不在稿件段落中"。

## 测试 C：范围词风险（引擎应转人工确认）

statement="首次实现全面空气稳定"，evidence_loc 段落无比较性数据 → overclaim_risk 进 manual_confirmations。

## 冒烟

```bash
python3 scripts/contribution_align.py --work tA --out outA
```
