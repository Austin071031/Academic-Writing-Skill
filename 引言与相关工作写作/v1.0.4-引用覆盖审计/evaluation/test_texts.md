# 合成测试文本（标注：全部合成）

## 测试 A：裸论断（引擎应列出）

binding 写 {"sentence":"已有工作普遍忽视长时稳定性","claim_type":"group_overview","entry_ids":["R002"]}
→ naked_claims（group_overview 需 ≥2）。

## 测试 B：关键工作漏引（引擎应转人工确认）

R001 分类 key 且未被任何 binding 引用 → uncovered_key_works + manual_confirmations。

## 测试 C：分类缺口（引擎应报）

库 5 条只分类 3 条 → classification_issues 含"未分类"×2。

## 冒烟

```bash
python3 scripts/coverage_audit.py --work tA --out outA
```
