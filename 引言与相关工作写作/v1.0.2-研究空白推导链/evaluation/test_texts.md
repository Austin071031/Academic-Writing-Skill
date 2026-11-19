# 合成测试文本（标注：全部合成）

## 测试 A：数字泄漏（引擎应报）

gap_statement 写"24 小时以上暴露电阻增加 12%"，但前提 quote 均无"12"，
response_evidence_loc 段落也无 → number_leaks 命中。

## 测试 B：无前提空白（引擎应判 fail）

gaps=[{gap_statement:"相关研究较少", premises:[]}] → issues 含"无前提"。

## 测试 C：冲突模式（应通过）

两条前提 quote 分别给出相互矛盾的结论，gap_statement="X 的判定尚无定论" → pass。

## 冒烟

```bash
python3 scripts/gap_chain.py --work tA --out outA
```
