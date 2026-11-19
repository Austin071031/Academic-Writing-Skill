# 完整标注示例（合成稿件，非正式案例结果）

> 本示例全部内容为说明接口与流程的合成数据，非平台正式案例。

## 输入（合成稿件摘录）

```markdown
## Abstract
Perovskite solar cells (PSCs) have attracted considerable attention. We fabricated
devices with a certified efficiency of 23.4% [1]. The hole transport layer (HTL) is
essential for charge extraction.

## Conclusion
We demonstrated perovskite solar cells with improved stability.
```

## 流程产物

1. `term_engine seed` 输出候选（节选）：

```json
{"terms":[
 {"term_id":"T001","term":"perovskite solar cells","acronym":"PSCs","occurrences":2,
  "source":"frequent_phrase+acronym","locked":false},
 {"term_id":"T002","term":"hole transport layer","acronym":"HTL","occurrences":1,
  "source":"acronym","locked":false}]}
```

2. Agent 审定后 `glossary.json`：

```json
{"terms":[
 {"term_id":"T001","term":"perovskite solar cells","acronym":"PSCs","locked":true,
  "locked_translation":"钙钛矿太阳能电池","rationale":"学科惯例译名"},
 {"term_id":"T002","term":"hole transport layer","acronym":"HTL","locked":true,
  "locked_translation":"空穴传输层","rationale":"材料学惯例译名"}]}
```

3. Agent 译文（translations.jsonl）：

```jsonl
{"seg_id":"P001-s1","translation":"钙钛矿太阳能电池（PSCs）受到广泛关注。"}
{"seg_id":"P001-s2","translation":"我们制备的器件认证效率为23.4%[1]。"}
{"seg_id":"P001-s3","translation":"空穴传输层（HTL）对电荷抽取至关重要。"}
{"seg_id":"P002-s1","translation":"我们展示了稳定性改善的钙钛矿光伏电池。"}
```

4. `term_engine audit` 检出：P002-s1 源含 "perovskite solar cells" 而译文用
   “钙钛矿光伏电池”，未用锁定译名 → finding TERM-001（术语未锁定，中）。
   修订译文为“……钙钛矿太阳能电池。”后复检清零。

## 示意输出（示例，非正式案例结果）

- translation_full.md：纯译文含术语统一后全文。
- term_audit.json：`{"summary":{"terms_locked":2,"violations":0}}`（修订后）。
- result.json：`status="success"`，evidence_map 含逐句段原文/译文对照。
